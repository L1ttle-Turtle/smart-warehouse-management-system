from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import aliased, joinedload

from ..audit import log_audit_event
from ..extensions import db
from ..models import Product, Stocktake, StocktakeDetail, Warehouse, WarehouseLocation
from ..permissions import get_current_user, permission_required
from ..schemas import StocktakeSchema
from ..serializers import serialize_stocktake
from ..services.inventory import build_stocktake_detail_values, confirm_stocktake, validate_location_in_warehouse
from ..utils import generate_code, utc_now

stocktakes_bp = Blueprint("stocktakes", __name__)


SORT_FIELDS = {
    "stocktake_code": Stocktake.stocktake_code,
    "status": Stocktake.status,
    "created_at": Stocktake.created_at,
    "updated_at": Stocktake.updated_at,
    "confirmed_at": Stocktake.confirmed_at,
    "cancelled_at": Stocktake.cancelled_at,
}


def normalize_optional_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def parse_optional_int_arg(name):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None

    raw_value = raw_value.strip()
    if not raw_value:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")

    try:
        return int(raw_value)
    except ValueError:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")


def parse_positive_int_arg(name, default, *, minimum=1, maximum=100):
    raw_value = request.args.get(name)
    if raw_value is None:
        return default

    raw_value = raw_value.strip()
    if not raw_value:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")

    try:
        parsed_value = int(raw_value)
    except ValueError:
        abort(400, description=f"{name} phải là số nguyên hợp lệ.")

    if parsed_value < minimum or parsed_value > maximum:
        abort(400, description=f"{name} phải nằm trong khoảng {minimum}-{maximum}.")
    return parsed_value


def get_pagination_params():
    page = parse_positive_int_arg("page", 1)
    page_size = parse_positive_int_arg("page_size", 10)
    return page, page_size


def build_pagination_payload(pagination):
    return {
        "items": [serialize_stocktake(item) for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "page_size": pagination.per_page,
    }


def apply_sort(query):
    sort_by = normalize_optional_text(request.args.get("sort_by")) or "created_at"
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    if sort_by not in SORT_FIELDS:
        abort(400, description="sort_by không hợp lệ.")
    if sort_order not in {"asc", "desc"}:
        abort(400, description="sort_order không hợp lệ.")

    column = SORT_FIELDS[sort_by]
    if sort_order == "asc":
        return query.order_by(column.asc(), Stocktake.id.asc())
    return query.order_by(column.desc(), Stocktake.id.desc())


def validate_warehouse(warehouse_id):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse:
        abort(400, description="Kho không hợp lệ.")
    return warehouse


def validate_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(400, description="Sản phẩm không hợp lệ.")
    if product.status != "active":
        abort(400, description="Sản phẩm đang ngừng hoạt động, không thể kiểm kê.")
    return product


def validate_stocktake_payload(payload):
    warehouse_id = payload["warehouse_id"]
    validate_warehouse(warehouse_id)

    seen_pairs = set()
    for detail in payload.get("details", []):
        validate_product(detail["product_id"])
        try:
            validate_location_in_warehouse(detail["location_id"], warehouse_id)
        except ValueError as exc:
            abort(400, description=str(exc))

        if float(detail["actual_quantity"]) < 0:
            abort(400, description="Số lượng thực tế phải lớn hơn hoặc bằng 0.")

        pair = (detail["product_id"], detail["location_id"])
        if pair in seen_pairs:
            abort(400, description="Không được trùng sản phẩm và vị trí trong cùng phiếu kiểm kê.")
        seen_pairs.add(pair)


def normalize_payload(payload):
    normalized_payload = dict(payload)
    if "note" in normalized_payload:
        normalized_payload["note"] = normalize_optional_text(normalized_payload["note"])
    normalized_payload["details"] = [
        {
            **item,
            "actual_quantity": float(item["actual_quantity"]),
            "note": normalize_optional_text(item.get("note")),
        }
        for item in normalized_payload.get("details", [])
    ]
    return normalized_payload


def sync_stocktake_details(stocktake, details):
    stocktake.details.clear()
    db.session.flush()
    for item in build_stocktake_detail_values(stocktake.warehouse_id, details):
        stocktake.details.append(
            StocktakeDetail(
                product_id=item["product_id"],
                location_id=item["location_id"],
                system_quantity=item["system_quantity"],
                actual_quantity=item["actual_quantity"],
                difference_quantity=item["difference_quantity"],
                note=item.get("note"),
            )
        )


def audit_stocktake_change(action, actor_user_id, stocktake):
    log_audit_event(
        action,
        "stocktake",
        f"{action.split('.')[1].capitalize()} phiếu kiểm kê {stocktake.stocktake_code}.",
        actor_user_id=actor_user_id,
        entity_id=stocktake.id,
        entity_label=stocktake.stocktake_code,
    )


def claim_draft_stocktake_for_mutation(stocktake_id, lock_status, error_message):
    claimed_rows = (
        db.session.query(Stocktake)
        .filter(
            Stocktake.id == stocktake_id,
            Stocktake.status == "draft",
        )
        .update({"status": lock_status}, synchronize_session=False)
    )
    if claimed_rows == 0:
        stocktake = db.session.get(Stocktake, stocktake_id)
        if not stocktake:
            abort(404)
        abort(400, description=error_message)

    stocktake = db.session.get(Stocktake, stocktake_id)
    stocktake.status = "draft"
    return stocktake


@stocktakes_bp.get("/stocktakes")
@jwt_required()
@permission_required("inventory.view")
def list_stocktakes():
    warehouse_alias = aliased(Warehouse)
    query = (
        Stocktake.query.join(warehouse_alias, Stocktake.warehouse_id == warehouse_alias.id)
        .options(
            joinedload(Stocktake.warehouse),
            joinedload(Stocktake.creator),
            joinedload(Stocktake.confirmer),
            joinedload(Stocktake.canceller),
            joinedload(Stocktake.details).joinedload(StocktakeDetail.product),
            joinedload(Stocktake.details).joinedload(StocktakeDetail.location),
        )
    )

    search = normalize_optional_text(request.args.get("q")) or normalize_optional_text(request.args.get("search"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Stocktake.stocktake_code.ilike(like_term),
                Stocktake.note.ilike(like_term),
                warehouse_alias.warehouse_code.ilike(like_term),
                warehouse_alias.warehouse_name.ilike(like_term),
            )
        )

    status = normalize_optional_text(request.args.get("status"))
    if status:
        query = query.filter(Stocktake.status == status)

    warehouse_id = parse_optional_int_arg("warehouse_id")
    if warehouse_id is not None:
        validate_warehouse(warehouse_id)
        query = query.filter(Stocktake.warehouse_id == warehouse_id)

    page, page_size = get_pagination_params()
    pagination = apply_sort(query).paginate(page=page, per_page=page_size, error_out=False)
    return jsonify(build_pagination_payload(pagination))


@stocktakes_bp.post("/stocktakes")
@jwt_required()
@permission_required("inventory.manage")
def create_stocktake():
    current_user = get_current_user()
    payload = normalize_payload(StocktakeSchema().load(request.get_json() or {}))
    validate_stocktake_payload(payload)

    stocktake = Stocktake(
        stocktake_code=generate_code("STK"),
        warehouse_id=payload["warehouse_id"],
        created_by=current_user.id,
        note=payload.get("note"),
    )
    db.session.add(stocktake)
    db.session.flush()
    sync_stocktake_details(stocktake, payload["details"])
    audit_stocktake_change("stocktakes.created", current_user.id, stocktake)
    db.session.commit()
    return jsonify({"item": serialize_stocktake(stocktake)}), 201


@stocktakes_bp.get("/stocktakes/<int:stocktake_id>")
@jwt_required()
@permission_required("inventory.view")
def get_stocktake(stocktake_id):
    stocktake = (
        Stocktake.query.options(
            joinedload(Stocktake.warehouse),
            joinedload(Stocktake.creator),
            joinedload(Stocktake.confirmer),
            joinedload(Stocktake.canceller),
            joinedload(Stocktake.details).joinedload(StocktakeDetail.product),
            joinedload(Stocktake.details).joinedload(StocktakeDetail.location),
        )
        .filter(Stocktake.id == stocktake_id)
        .first_or_404()
    )
    return jsonify({"item": serialize_stocktake(stocktake)})


@stocktakes_bp.put("/stocktakes/<int:stocktake_id>")
@jwt_required()
@permission_required("inventory.manage")
def update_stocktake(stocktake_id):
    current_user = get_current_user()
    try:
        stocktake = claim_draft_stocktake_for_mutation(
            stocktake_id,
            "editing",
            "Chỉ phiếu kiểm kê ở trạng thái nháp mới có thể chỉnh sửa.",
        )
        payload = normalize_payload(StocktakeSchema().load(request.get_json() or {}))
        validate_stocktake_payload(payload)

        stocktake.warehouse_id = payload["warehouse_id"]
        stocktake.note = payload.get("note")
        sync_stocktake_details(stocktake, payload["details"])
        audit_stocktake_change("stocktakes.updated", current_user.id, stocktake)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"item": serialize_stocktake(stocktake)})


@stocktakes_bp.post("/stocktakes/<int:stocktake_id>/confirm")
@jwt_required()
@permission_required("inventory.manage")
def confirm_stocktake_route(stocktake_id):
    current_user = get_current_user()
    try:
        stocktake = claim_draft_stocktake_for_mutation(
            stocktake_id,
            "confirming",
            "Chỉ phiếu kiểm kê ở trạng thái nháp mới có thể xác nhận.",
        )
        confirm_stocktake(stocktake, current_user.id)
        audit_stocktake_change("stocktakes.confirmed", current_user.id, stocktake)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(400, description=str(exc))
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"item": serialize_stocktake(stocktake)})


@stocktakes_bp.post("/stocktakes/<int:stocktake_id>/cancel")
@jwt_required()
@permission_required("inventory.manage")
def cancel_stocktake_route(stocktake_id):
    current_user = get_current_user()
    try:
        stocktake = claim_draft_stocktake_for_mutation(
            stocktake_id,
            "cancelling",
            "Chỉ phiếu kiểm kê ở trạng thái nháp mới có thể hủy.",
        )
        stocktake.status = "cancelled"
        stocktake.cancelled_by = current_user.id
        stocktake.cancelled_at = utc_now()
        audit_stocktake_change("stocktakes.cancelled", current_user.id, stocktake)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"item": serialize_stocktake(stocktake)})

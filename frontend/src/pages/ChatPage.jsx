import { SendOutlined } from '@ant-design/icons';
import { Button, Card, Input, List, Select, Space, Spin, Typography, message } from 'antd';
import { useCallback, useEffect, useEffectEvent, useMemo, useState } from 'react';

import api from '../api/client';
import { useAuth } from '../auth/useAuth';
import SectionCard from '../components/SectionCard';
import { formatDateTime } from '../utils/format';

function ChatPage() {
  const { socket, user } = useAuth();
  const [users, setUsers] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const conversationId = selectedConversation?.id;

  const fetchConversations = useCallback(async () => {
    const [userResponse, conversationResponse] = await Promise.all([
      api.get('/chat/users'),
      api.get('/chat/conversations'),
    ]);
    setUsers((userResponse.data.items || []).filter((item) => item.id !== user?.id));
    const nextConversations = conversationResponse.data.items || [];
    setConversations(nextConversations);
    setSelectedConversation((currentConversation) => {
      if (!currentConversation) {
        return nextConversations[0] || null;
      }
      return nextConversations.find((item) => item.id === currentConversation.id) || nextConversations[0] || null;
    });
  }, [user?.id]);

  useEffect(() => {
    fetchConversations().catch((error) => {
      message.error(error.response?.data?.message || 'Không tải được danh sách chat.');
    });
  }, [fetchConversations]);

  useEffect(() => {
    if (!conversationId) {
      return;
    }
    setLoading(true);
    api.get(`/chat/conversations/${conversationId}/messages`)
      .then((response) => setMessages(response.data.items || []))
      .catch((error) => {
        message.error(error.response?.data?.message || 'Không tải được tin nhắn.');
      })
      .finally(() => setLoading(false));
  }, [conversationId]);

  const handleIncomingMessage = useEffectEvent((payload) => {
    setConversations((current) => current.map((item) => (
      item.id === payload.conversation_id ? { ...item, last_message: payload } : item
    )));
    if (payload.conversation_id === selectedConversation?.id) {
      setMessages((current) => [...current, payload]);
    }
  });

  useEffect(() => {
    if (!socket) {
      return undefined;
    }
    const onReceive = (payload) => handleIncomingMessage(payload);
    socket.on('chat:receive', onReceive);
    return () => socket.off('chat:receive', onReceive);
  }, [socket]);

  const availableUsers = useMemo(
    () => users.filter((entry) => !conversations.some((conversation) => conversation.peer?.id === entry.id)),
    [users, conversations],
  );

  return (
    <SectionCard
      title="Chat nội bộ"
      subtitle="Trao đổi 1-1 nhanh giữa các nhân sự để xử lý kho, vận đơn và công việc hằng ngày."
      extra={(
        <Select
          style={{ width: 280 }}
          placeholder="Bắt đầu chat với..."
          options={availableUsers.map((entry) => ({
            label: `${entry.full_name} (${entry.role_name || 'Chưa có vai trò'})`,
            value: entry.id,
          }))}
          onChange={async (userId) => {
            try {
              const response = await api.post('/chat/conversations/direct', { user_id: userId });
              await fetchConversations();
              setSelectedConversation(response.data.item);
            } catch (error) {
              message.error(error.response?.data?.message || 'Không tạo được cuộc trò chuyện.');
            }
          }}
        />
      )}
    >
      <div className="chat-shell">
        <Card className="page-card" styles={{ body: { padding: 0 } }}>
          <List
            dataSource={conversations}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  paddingInline: 18,
                  background: selectedConversation?.id === item.id ? 'rgba(124, 58, 237, 0.08)' : 'transparent',
                }}
                onClick={() => setSelectedConversation(item)}
              >
                <List.Item.Meta
                  title={item.peer?.full_name || 'Cuộc trò chuyện'}
                  description={item.last_message?.content || 'Chưa có tin nhắn'}
                />
              </List.Item>
            )}
          />
        </Card>

        <Card className="page-card">
          {selectedConversation ? (
            <Space orientation="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Typography.Title level={4} style={{ marginBottom: 0 }}>
                  {selectedConversation.peer?.full_name || 'Cuộc trò chuyện'}
                </Typography.Title>
                <Typography.Text type="secondary">
                  {selectedConversation.peer?.role_name || 'Chưa có vai trò'}
                </Typography.Text>
              </div>

              <div className="chat-messages">
                {loading ? <Spin /> : messages.map((item) => (
                  <div
                    key={`${item.id}-${item.sent_at}`}
                    className={`message-bubble ${item.sender_id === user?.id ? 'message-self' : 'message-peer'}`}
                  >
                    <Typography.Text strong>{item.sender_name}</Typography.Text>
                    <div>{item.content}</div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {formatDateTime(item.sent_at)}
                    </Typography.Text>
                  </div>
                ))}
              </div>

              <Input.TextArea
                rows={4}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Nhập nội dung cần trao đổi..."
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={async () => {
                  if (!draft.trim()) {
                    message.warning('Vui lòng nhập nội dung tin nhắn.');
                    return;
                  }
                  try {
                    const response = await api.post(
                      `/chat/conversations/${selectedConversation.id}/messages`,
                      { content: draft },
                    );
                    setMessages((current) => [...current, response.data.item]);
                    setDraft('');
                    fetchConversations();
                  } catch (error) {
                    message.error(error.response?.data?.message || 'Không gửi được tin nhắn.');
                  }
                }}
              >
                Gửi tin
              </Button>
            </Space>
          ) : (
            <Typography.Text type="secondary">Chọn một cuộc trò chuyện để bắt đầu.</Typography.Text>
          )}
        </Card>
      </div>
    </SectionCard>
  );
}

export default ChatPage;

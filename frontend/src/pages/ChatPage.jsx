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
      api.get('/directory/users'),
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
      message.error(error.response?.data?.message || 'Khong tai duoc chat.');
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
        message.error(error.response?.data?.message || 'Khong tai duoc tin nhan.');
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
    () => users.filter((entry) => !conversations.some((conversation) => conversation.peer?.user_id === entry.id)),
    [users, conversations],
  );

  return (
    <SectionCard
      title="Chat noi bo"
      subtitle="Trao doi 1-1 theo thoi gian thuc de xu ly kho, van don va cong viec."
      extra={(
        <Select
          style={{ width: 280 }}
          placeholder="Bat dau chat voi..."
          options={availableUsers.map((entry) => ({ label: `${entry.full_name} (${entry.role})`, value: entry.id }))}
          onChange={async (userId) => {
            try {
              const response = await api.post('/chat/conversations/direct', { user_id: userId });
              await fetchConversations();
              setSelectedConversation(response.data.item);
            } catch (error) {
              message.error(error.response?.data?.message || 'Khong tao duoc cuoc tro chuyen.');
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
                  background: selectedConversation?.id === item.id ? 'rgba(31, 111, 95, 0.08)' : 'transparent',
                }}
                onClick={() => setSelectedConversation(item)}
              >
                <List.Item.Meta
                  title={item.peer?.full_name || 'Conversation'}
                  description={item.last_message?.content || 'Chua co tin nhan'}
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
                  {selectedConversation.peer?.full_name || 'Conversation'}
                </Typography.Title>
                <Typography.Text type="secondary">
                  {selectedConversation.peer?.role || 'No role'}
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
                placeholder="Nhap noi dung can trao doi..."
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={async () => {
                  if (!draft.trim()) {
                    return;
                  }
                  try {
                    await api.post(`/chat/conversations/${selectedConversation.id}/messages`, { content: draft });
                    setDraft('');
                    fetchConversations();
                  } catch (error) {
                    message.error(error.response?.data?.message || 'Khong gui duoc tin nhan.');
                  }
                }}
              >
                Gui tin
              </Button>
            </Space>
          ) : (
            <Typography.Text type="secondary">Chon mot cuoc tro chuyen de bat dau.</Typography.Text>
          )}
        </Card>
      </div>
    </SectionCard>
  );
}

export default ChatPage;

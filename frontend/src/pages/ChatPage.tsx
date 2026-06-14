/**
 * Переписка по объявлению: поиск/создание чата, опрос новых сообщений.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Avatar,
  Paper,
  CircularProgress,
  Alert,
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
} from '@mui/material';
import { Send, ArrowBack, Message as MessageIcon } from '@mui/icons-material';
import { Chat, Message } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const ChatPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [chat, setChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageText, setMessageText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (id) {
      loadChat();
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /** Прокрутка области сообщений к последнему элементу. */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /** Находит или создаёт чат по id объявления из URL, затем помечает прочитанным и запускает polling. */
  const loadChat = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Создаем или получаем чат по объявлению
      let chatData: Chat;
      try {
        // Пытаемся найти существующий чат
        const chats = await apiService.getChats();
        const existingChat = chats.find(c => c.ad.id === Number(id));
        
        if (existingChat) {
          chatData = existingChat;
        } else {
          // Создаем новый чат
          chatData = await apiService.createChat(Number(id));
        }
      } catch (err) {
        // Если не удалось создать, пробуем получить по ID
        chatData = await apiService.createChat(Number(id));
      }
      
      setChat(chatData);
      await loadMessages(chatData.id);
      
      // Помечаем сообщения как прочитанные
      await apiService.markMessagesRead(chatData.id);
      
      // Начинаем опрос новых сообщений
      startPolling(chatData.id);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка загрузки чата');
      console.error('Error loading chat:', err);
    } finally {
      setLoading(false);
    }
  };

  /** Загружает все сообщения выбранного чата. */
  const loadMessages = async (chatId: number) => {
    try {
      const messagesData = await apiService.getMessages(chatId);
      // Убеждаемся, что это массив
      setMessages(Array.isArray(messagesData) ? messagesData : []);
    } catch (err) {
      console.error('Error loading messages:', err);
      setMessages([]);
    }
  };

  /** Периодический опрос сообщений и mark read для входящих от собеседника. */
  const startPolling = (chatId: number) => {
    // Очищаем предыдущий интервал
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    
    // Опрашиваем новые сообщения каждые 3 секунды
    pollIntervalRef.current = setInterval(async () => {
      try {
        const messagesData = await apiService.getMessages(chatId);
        // Убеждаемся, что это массив
        const messagesArray = Array.isArray(messagesData) ? messagesData : [];
        setMessages(messagesArray);
        
        // Помечаем новые сообщения как прочитанные
        const hasUnread = messagesArray.some(
          m => !m.is_read && m.sender.id !== user?.id
        );
        if (hasUnread) {
          await apiService.markMessagesRead(chatId);
        }
      } catch (err) {
        console.error('Error polling messages:', err);
      }
    }, 3000);
  };

  /** Отправка текста из поля ввода в текущий чат. */
  const handleSendMessage = async () => {
    if (!messageText.trim() || !chat) return;
    
    try {
      setSending(true);
      const newMessage = await apiService.sendMessage(chat.id, { text: messageText });
      setMessages([...messages, newMessage]);
      setMessageText('');
      
      // Помечаем сообщения как прочитанные
      await apiService.markMessagesRead(chat.id);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка отправки сообщения');
    } finally {
      setSending(false);
    }
  };

  /** Enter без Shift отправляет сообщение. */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !chat) {
    return (
      <Box>
        <Alert severity="error">{error}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Вернуться назад
        </Button>
      </Box>
    );
  }

  if (!chat) {
    return (
      <Box>
        <Alert severity="warning">Чат не найден</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Вернуться назад
        </Button>
      </Box>
    );
  }

  const otherUser = chat.tenant.id === user?.id ? chat.landlord : chat.tenant;
  return (
    <Box>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate(-1)}
        sx={{ mb: 2 }}
      >
        Назад
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card sx={{ overflow: 'hidden' }}>
        <CardContent>
          {/* Заголовок чата */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar sx={{ mr: 2 }}>{otherUser.username[0].toUpperCase()}</Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6">{otherUser.username}</Typography>
              <Typography variant="body2" color="text.secondary">
                Чат по объявлению: {chat.ad.title}
              </Typography>
            </Box>
            <Button
              variant="outlined"
              size="small"
              onClick={() => navigate(`/ads/${chat.ad.id}`)}
            >
              Перейти к объявлению
            </Button>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Сообщения */}
          <Box
            sx={{
              height: '500px',
              overflowY: 'auto',
              mb: 2,
              p: 1,
              bgcolor: '#f0f3ff',
              borderRadius: 3,
            }}
          >
            {messages.length === 0 ? (
              <Box textAlign="center" py={4}>
                <MessageIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Пока нет сообщений. Начните общение!
                </Typography>
              </Box>
            ) : (
              <List>
                {messages.map((message) => {
                  const isOwn = message.sender.id === user?.id;
                  return (
                    <ListItem
                      key={message.id}
                      sx={{
                        flexDirection: isOwn ? 'row-reverse' : 'row',
                        alignItems: 'flex-start',
                      }}
                    >
                      <ListItemAvatar>
                        <Avatar>{message.sender.username[0].toUpperCase()}</Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Paper
                            sx={{
                              p: 1.5,
                              bgcolor: isOwn ? 'primary.main' : 'grey.200',
                              color: isOwn ? 'white' : 'text.primary',
                              maxWidth: '70%',
                              borderRadius: 2,
                            }}
                          >
                            <Typography variant="body1">{message.text}</Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                display: 'block',
                                mt: 0.5,
                                opacity: 0.8,
                              }}
                            >
                              {new Date(message.created_at).toLocaleTimeString()}
                            </Typography>
                          </Paper>
                        }
                        secondary={
                          !isOwn && (
                            <Typography variant="caption" color="text.secondary">
                              {message.sender.username}
                            </Typography>
                          )
                        }
                        sx={{ textAlign: isOwn ? 'right' : 'left' }}
                      />
                    </ListItem>
                  );
                })}
                <div ref={messagesEndRef} />
              </List>
            )}
          </Box>

          {/* Форма отправки сообщения */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder="Введите сообщение..."
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={sending}
            />
            <IconButton
              color="primary"
              onClick={handleSendMessage}
              disabled={!messageText.trim() || sending}
              sx={{ alignSelf: 'flex-end' }}
            >
              {sending ? <CircularProgress size={24} /> : <Send />}
            </IconButton>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ChatPage;

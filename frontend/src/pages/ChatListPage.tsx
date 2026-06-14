/**
 * Список чатов слева и панель переписки справа; поиск по участникам и объявлению.
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  Typography,
  Avatar,
  Paper,
  CircularProgress,
  Alert,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Badge,
  InputAdornment,
} from '@mui/material';
import { Send, Message as MessageIcon, Search } from '@mui/icons-material';
import { Chat, Message } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const ChatListPage: React.FC = () => {
  const { user } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messageText, setMessageText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadChats();
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (selectedChat) {
      loadMessages(selectedChat.id);
      startPolling(selectedChat.id);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [selectedChat]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /** Прокрутка ленты сообщений вниз при обновлении. */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /** Загрузка всех чатов пользователя. */
  const loadChats = async () => {
    try {
      setLoading(true);
      setError(null);
      const chatsData = await apiService.getChats();
      // Убеждаемся, что это массив
      setChats(Array.isArray(chatsData) ? chatsData : []);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка загрузки чатов');
      console.error('Error loading chats:', err);
      setChats([]);
    } finally {
      setLoading(false);
    }
  };

  /** Сообщения выбранного чата и отметка прочитанного на сервере. */
  const loadMessages = async (chatId: number) => {
    try {
      setLoadingMessages(true);
      const messagesData = await apiService.getMessages(chatId);
      const messagesArray = Array.isArray(messagesData) ? messagesData : [];
      setMessages(messagesArray);
      
      // Помечаем сообщения как прочитанные
      await apiService.markMessagesRead(chatId);
    } catch (err) {
      console.error('Error loading messages:', err);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  /** Интервальный опрос для активного чата с обновлением списка при новых входящих. */
  const startPolling = (chatId: number) => {
    // Очищаем предыдущий интервал
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    
    // Опрашиваем новые сообщения каждые 3 секунды
    pollIntervalRef.current = setInterval(async () => {
      try {
        const messagesData = await apiService.getMessages(chatId);
        const messagesArray = Array.isArray(messagesData) ? messagesData : [];
        setMessages(messagesArray);
        
        // Помечаем новые сообщения как прочитанные
        const hasUnread = messagesArray.some(
          m => !m.is_read && m.sender.id !== user?.id
        );
        if (hasUnread) {
          await apiService.markMessagesRead(chatId);
          // Обновляем список чатов для обновления счетчика непрочитанных
          loadChats();
        }
      } catch (err) {
        console.error('Error polling messages:', err);
      }
    }, 3000);
  };

  /** Выбор строки в списке слева для отображения переписки. */
  const handleChatSelect = (chat: Chat) => {
    setSelectedChat(chat);
    setMessageText('');
  };

  /** Отправка сообщения в выбранный чат и обновление списка диалогов. */
  const handleSendMessage = async () => {
    if (!messageText.trim() || !selectedChat) return;
    
    try {
      setSending(true);
      const newMessage = await apiService.sendMessage(selectedChat.id, { text: messageText });
      setMessages([...messages, newMessage]);
      setMessageText('');
      
      // Помечаем сообщения как прочитанные
      await apiService.markMessagesRead(selectedChat.id);
      
      // Обновляем список чатов
      loadChats();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка отправки сообщения');
    } finally {
      setSending(false);
    }
  };

  /** Enter отправляет сообщение без новой строки. */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  /** Заглушка счётчика непрочитанных (расширяемо полем на бэкенде). */
  const getUnreadCount = (chat: Chat): number => {
    // Подсчитываем непрочитанные сообщения (требует загрузки сообщений)
    // Для простоты возвращаем 0, можно улучшить, добавив поле в Chat
    return 0;
  };

  const filteredChats = chats.filter(chat => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      chat.ad.title.toLowerCase().includes(query) ||
      chat.tenant.username.toLowerCase().includes(query) ||
      chat.landlord.username.toLowerCase().includes(query)
    );
  });

  const otherUser = selectedChat
    ? (selectedChat.tenant.id === user?.id ? selectedChat.landlord : selectedChat.tenant)
    : null;

  return (
    <Box
      sx={{
        display: 'flex',
        height: 'calc(100vh - 64px - 48px)', // Высота экрана минус Header (64px) минус отступы Container (48px)
        overflow: 'hidden',
        position: 'relative',
        margin: '-24px',
        width: 'calc(100% + 48px)',
      }}
    >
      {/* Список чатов слева */}
      <Box
        sx={{
          width: '350px',
          borderRight: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: 'background.paper',
        }}
      >
        {/* Заголовок и поиск */}
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em' }}>
            Messenger
          </Typography>
          <Typography variant="h6" gutterBottom>
            Чаты
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Поиск чатов..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </Box>

        {/* Список чатов */}
        <Box sx={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
              <CircularProgress />
            </Box>
          ) : filteredChats.length === 0 ? (
              <Box textAlign="center" py={4}>
              <MessageIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                {searchQuery ? 'Чаты не найдены' : 'У вас пока нет чатов'}
              </Typography>
            </Box>
          ) : (
            <List>
              {filteredChats.map((chat) => {
                const chatOtherUser = chat.tenant.id === user?.id ? chat.landlord : chat.tenant;
                const isSelected = selectedChat?.id === chat.id;
                const unreadCount = getUnreadCount(chat);
                
                return (
                  <ListItem
                    key={chat.id}
                    button
                    selected={isSelected}
                    onClick={() => handleChatSelect(chat)}
                    sx={{
                      bgcolor: isSelected ? 'action.selected' : 'transparent',
                      '&:hover': {
                        bgcolor: 'action.hover',
                      },
                    }}
                  >
                    <ListItemAvatar>
                      <Badge badgeContent={unreadCount} color="primary">
                          <Avatar sx={{ boxShadow: '0 8px 16px rgba(17,28,45,0.12)' }}>
                            {chatOtherUser.username[0].toUpperCase()}
                          </Avatar>
                      </Badge>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="subtitle1" noWrap>
                            {chatOtherUser.username}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Typography variant="body2" color="text.secondary" noWrap>
                          {chat.ad.title}
                        </Typography>
                      }
                    />
                  </ListItem>
                );
              })}
            </List>
          )}
        </Box>
      </Box>

      {/* Переписка справа */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', bgcolor: 'grey.50' }}>
        {selectedChat ? (
          <>
            {/* Заголовок чата */}
            <Box
              sx={{
                p: 2,
                borderBottom: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ mr: 2 }}>{otherUser?.username[0].toUpperCase()}</Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h6">{otherUser?.username}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedChat.ad.title}
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Сообщения */}
            <Box
              sx={{
                flex: 1,
                overflowY: 'auto',
                p: 2,
              }}
            >
              {loadingMessages ? (
                <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                  <CircularProgress />
                </Box>
              ) : messages.length === 0 ? (
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
                          px: 0,
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
                                bgcolor: isOwn ? 'primary.main' : 'white',
                                color: isOwn ? 'white' : 'text.primary',
                                maxWidth: '70%',
                                borderRadius: 2,
                                boxShadow: 1,
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
                              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
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
            <Box
              sx={{
                p: 2,
                borderTop: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            >
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}
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
            </Box>
          </>
        ) : (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100%',
            }}
          >
            <Box textAlign="center">
              <MessageIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Выберите чат для начала переписки
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default ChatListPage;


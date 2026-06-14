import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
} from '@mui/material';
import {
  AccountCircle,
  Favorite,
  Add,
  AdminPanelSettings,
  Message,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

/** Шапка приложения: быстрые действия и меню аккаунта. */
const Header: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  /** Открывает выпадающее меню по клику на аватар. */
  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  /** Закрывает меню без смены страницы. */
  const handleClose = () => {
    setAnchorEl(null);
  };

  /** Выход из аккаунта и переход на главную. */
  const handleLogout = () => {
    logout();
    handleClose();
    navigate('/');
  };

  /** Переход в профиль. */
  const handleProfile = () => {
    navigate('/profile');
    handleClose();
  };

  /** Переход к списку избранного. */
  const handleFavorites = () => {
    navigate('/favorites');
    handleClose();
  };

  /** Панель модерации (для администратора). */
  const handleModeration = () => {
    navigate('/moderation');
  };

  /** Список чатов пользователя. */
  const handleChats = () => {
    navigate('/chats');
  };

  return (
    <AppBar position="sticky">
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ cursor: 'pointer', fontWeight: 700, letterSpacing: '-0.01em' }}
          onClick={() => navigate('/')}
        >
          Architectural Curator
        </Typography>
        
        <Box sx={{ flexGrow: 1 }} />
        
        {isAuthenticated ? (
          <>
            <IconButton
              color="inherit"
              onClick={() => navigate('/ads/new')}
              title="Создать объявление"
            >
              <Add />
            </IconButton>
            
            <IconButton
              color="inherit"
              onClick={handleFavorites}
              title="Избранное"
            >
              <Favorite />
            </IconButton>
            
            <IconButton
              color="inherit"
              onClick={handleChats}
              title="Чаты"
            >
              <Message />
            </IconButton>
            
            {user?.role === 'admin' && (
              <IconButton
                color="inherit"
                onClick={handleModeration}
                title="Панель модерации"
              >
                <AdminPanelSettings />
              </IconButton>
            )}
            
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              {user?.avatar ? (
                <Avatar src={user.avatar} sx={{ width: 32, height: 32 }} />
              ) : (
                <AccountCircle />
              )}
            </IconButton>
            
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem onClick={handleProfile}>Профиль</MenuItem>
              <MenuItem onClick={handleFavorites}>Избранное</MenuItem>
              {user?.role === 'admin' && (
                <MenuItem onClick={handleModeration}>
                  <AdminPanelSettings sx={{ mr: 1 }} />
                  Модерация
                </MenuItem>
              )}
              <MenuItem onClick={handleLogout}>Выйти</MenuItem>
            </Menu>
          </>
        ) : (
          <>
            <Button color="inherit" onClick={() => navigate('/login')} variant="text">
              Войти
            </Button>
            <Button color="inherit" onClick={() => navigate('/register')} variant="contained">
              Регистрация
            </Button>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Header;


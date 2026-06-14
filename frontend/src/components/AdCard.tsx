/** Карточка объявления в каталоге: превью, цена, избранное, переход в детали. */
import React from 'react';
import {
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  IconButton,
} from '@mui/material';
import {
  Favorite,
  FavoriteBorder,
  Visibility,
  LocationOn,
} from '@mui/icons-material';
import { Ad } from '../types';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface AdCardProps {
  ad: Ad;
  onToggleFavorite?: (adId: number) => void;
}

const AdCard: React.FC<AdCardProps> = ({ ad, onToggleFavorite }) => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  /** Навигация на детальную страницу объявления. */
  const handleClick = () => {
    navigate(`/ads/${ad.id}`);
  };

  /** Останавливает всплытие клика с карточки и переключает избранное. */
  const handleToggleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onToggleFavorite) {
      onToggleFavorite(ad.id);
    }
  };

  const primaryImage = ad.images.find(img => img.is_primary) || ad.images[0];
  const statusColor = ad.status === 'approved' ? 'success' : 
                     ad.status === 'rejected' ? 'error' : 'warning';

  return (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        cursor: 'pointer',
        transition: 'transform 0.25s ease, box-shadow 0.25s ease',
        '&:hover': {
          transform: 'translateY(-6px)',
          boxShadow: '0 24px 45px rgba(17, 28, 45, 0.1)',
        }
      }}
      onClick={handleClick}
    >
      {primaryImage && (
        <CardMedia
          component="img"
          height="200"
          image={primaryImage.image}
          alt={ad.title}
          sx={{ objectFit: 'cover', transition: 'transform 0.35s ease' }}
        />
      )}
      
      <CardContent sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Typography variant="h6" component="h2" noWrap sx={{ flexGrow: 1, mr: 1 }}>
            {ad.title}
          </Typography>
          {isAuthenticated && (
            <IconButton
              onClick={handleToggleFavorite}
              size="small"
              color={ad.is_favorite ? 'error' : 'default'}
            >
              {ad.is_favorite ? <Favorite /> : <FavoriteBorder />}
            </IconButton>
          )}
        </Box>
        
        <Typography 
          variant="body2" 
          color="text.secondary" 
          sx={{ 
            mb: 1,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {ad.description}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <LocationOn fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
            {ad.location || 'Местоположение не указано'}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Chip 
            label={ad.category.name} 
            size="small" 
            color="primary" 
            variant="outlined" 
          />
          <Chip 
            label={ad.status === 'approved' ? 'Одобрено' : 
                   ad.status === 'rejected' ? 'Отклонено' : 'На модерации'} 
            size="small" 
            color={statusColor}
          />
          {ad.is_featured && (
            <Chip label="Рекомендуемое" size="small" color="secondary" />
          )}
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" color="primary" fontWeight="bold">
            {ad.price.toLocaleString()} ₽
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', ml: 'auto' }}>
            <Visibility fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
              {ad.views_count}
            </Typography>
          </Box>
        </Box>
      </CardContent>
      
      <CardActions>
        <Button size="small" onClick={handleClick}>
          Подробнее
        </Button>
        <Typography variant="body2" color="text.secondary">
          {new Date(ad.created_at).toLocaleDateString()}
        </Typography>
      </CardActions>
    </Card>
  );
};

export default AdCard;



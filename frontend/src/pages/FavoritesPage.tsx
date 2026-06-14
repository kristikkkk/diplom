/**
 * Список избранных объявлений текущего пользователя.
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import AdCard from '../components/AdCard';
import { Favorite } from '../types';
import { apiService } from '../services/api';

const FavoritesPage: React.FC = () => {
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFavorites();
  }, []);

  /** Загружает избранное с API. */
  const loadFavorites = async () => {
    try {
      setLoading(true);
      setError(null);
      const favoritesData = await apiService.getFavorites();
      setFavorites(favoritesData);
    } catch (err) {
      setError('Ошибка загрузки избранного');
      console.error('Error loading favorites:', err);
    } finally {
      setLoading(false);
    }
  };

  /** Удаляет из избранного или добавляет с перезагрузкой списка. */
  const handleToggleFavorite = async (adId: number) => {
    try {
      const favorite = favorites.find(f => f.ad.id === adId);
      if (favorite) {
        await apiService.removeFromFavorites(adId);
        setFavorites(favorites.filter(f => f.ad.id !== adId));
      } else {
        await apiService.addToFavorites(adId);
        // Перезагружаем список
        loadFavorites();
      }
    } catch (err) {
      console.error('Error toggling favorite:', err);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em' }}>
        Personal Collection
      </Typography>
      <Typography variant="h4" component="h1" gutterBottom>
        Избранные объявления
      </Typography>

      {favorites.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            У вас пока нет избранных объявлений
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Добавьте объявления в избранное, чтобы вернуться к ним позже
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {favorites.map((favorite) => (
            <Grid item xs={12} sm={6} md={4} key={favorite.id}>
              <AdCard
                ad={{ ...favorite.ad, is_favorite: true }}
                onToggleFavorite={handleToggleFavorite}
              />
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default FavoritesPage;


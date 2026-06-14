/**
 * Главная: каталог объявлений с поиском, фильтром по категории и сортировкой.
 */
import React, { useState, useEffect } from 'react';
import {
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Search, FilterList } from '@mui/icons-material';
import AdCard from '../components/AdCard';
import { Ad, Category, AdFilters } from '../types';
import { apiService } from '../services/api';

/** Кнопки фильтров: высота как у Outlined TextField/Select, скругление как у полей (не pill из темы). */
const filterActionButtonSx = {
  width: '100%',
  height: 56,
  minHeight: 56,
  borderRadius: 2,
  textTransform: 'none' as const,
  boxSizing: 'border-box' as const,
};

const HomePage: React.FC = () => {
  const [ads, setAds] = useState<Ad[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AdFilters>({
    search: '',
    category: undefined,
    ordering: '-created_at',
  });
  const [searchInput, setSearchInput] = useState('');

  useEffect(() => {
    loadData();
  }, [filters]);

  /** Переносит текст из поля поиска в фильтры и триггерит перезагрузку через useEffect. */
  const applySearch = () => {
    setFilters((prev) => ({ ...prev, search: searchInput.trim() }));
  };

  /** Загружает страницу объявлений и справочник категорий параллельно. */
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [adsData, categoriesData] = await Promise.all([
        apiService.getAds(filters),
        apiService.getCategories(),
      ]);
      
      setAds(adsData.results);
      setCategories(categoriesData);
    } catch (err) {
      setError('Ошибка загрузки данных');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  /** Обновляет фильтр категории из Select. */
  const handleCategoryChange = (event: any) => {
    setFilters(prev => ({
      ...prev,
      category: event.target.value || undefined,
    }));
  };

  /** Меняет поле сортировки списка объявлений. */
  const handleOrderingChange = (event: any) => {
    setFilters(prev => ({
      ...prev,
      ordering: event.target.value,
    }));
  };

  /** Добавляет или удаляет объявление из избранного и обновляет локальный список. */
  const handleToggleFavorite = async (adId: number) => {
    try {
      const ad = ads.find(a => a.id === adId);
      if (ad?.is_favorite) {
        await apiService.removeFromFavorites(adId);
      } else {
        await apiService.addToFavorites(adId);
      }
      
      // Обновляем локальное состояние
      setAds(prev => prev.map(a => 
        a.id === adId ? { ...a, is_favorite: !a.is_favorite } : a
      ));
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

  return (
    <Box>
      <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em', fontWeight: 700 }}>
        Curated Marketplace
      </Typography>
      <Typography variant="h3" component="h1" gutterBottom sx={{ mb: 3 }}>
        Найдите пространство под ваши цели
      </Typography>
      
      {/* Фильтры: доли 40/20/20/10/10 как 4fr 2fr 2fr 1fr 1fr */}
      <Box sx={{ mb: 4, p: 3, bgcolor: 'background.paper', borderRadius: 4, boxShadow: '0 20px 40px rgba(17, 28, 45, 0.06)' }}>
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            alignItems: 'stretch',
            gridTemplateColumns: {
              xs: 'minmax(0, 1fr)',
              md: 'minmax(0, 4fr) minmax(0, 2fr) minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr)',
            },
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <TextField
              fullWidth
              label="Поиск"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  applySearch();
                }
              }}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
              }}
            />
          </Box>

          <Box sx={{ minWidth: 0 }}>
            <FormControl fullWidth>
              <InputLabel>Категория</InputLabel>
              <Select
                value={filters.category || ''}
                onChange={handleCategoryChange}
                label="Категория"
              >
                <MenuItem value="">Все категории</MenuItem>
                {categories.map(category => (
                  <MenuItem key={category.id} value={category.id}>
                    {category.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ minWidth: 0 }}>
            <FormControl fullWidth>
              <InputLabel>Сортировка</InputLabel>
              <Select
                value={filters.ordering}
                onChange={handleOrderingChange}
                label="Сортировка"
              >
                <MenuItem value="-created_at">Новые сначала</MenuItem>
                <MenuItem value="created_at">Старые сначала</MenuItem>
                <MenuItem value="-price">Дорогие сначала</MenuItem>
                <MenuItem value="price">Дешевые сначала</MenuItem>
                <MenuItem value="-views_count">Популярные</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ minWidth: 0, display: 'flex', alignItems: 'stretch' }}>
            <Button
              variant="outlined"
              color="primary"
              onClick={applySearch}
              sx={filterActionButtonSx}
            >
              Искать
            </Button>
          </Box>

          <Box sx={{ minWidth: 0, display: 'flex', alignItems: 'stretch' }}>
            <Button
              variant="outlined"
              color="inherit"
              startIcon={<FilterList />}
              onClick={() => {
                setSearchInput('');
                setFilters({ search: '', category: undefined, ordering: '-created_at' });
              }}
              sx={filterActionButtonSx}
            >
              Сбросить
            </Button>
          </Box>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Список объявлений */}
      {ads.length === 0 ? (
        <Box textAlign="center" py={4}>
          <Typography variant="h6" color="text.secondary">
            Объявления не найдены
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Попробуйте изменить параметры поиска
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {ads.map(ad => (
            <Grid item xs={12} sm={6} md={4} key={ad.id}>
              <AdCard ad={ad} onToggleFavorite={handleToggleFavorite} />
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default HomePage;

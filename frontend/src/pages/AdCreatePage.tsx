/**
 * Форма создания объявления с загрузкой нескольких фотографий.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  IconButton,
  Paper,
  Chip,
} from '@mui/material';
import { Add, Delete, CloudUpload } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { AdCreate, Category } from '../types';
import { apiService } from '../services/api';

const AdCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [images, setImages] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<AdCreate & { category_id: number }>();

  React.useEffect(() => {
    loadCategories();
  }, []);

  /** Подгружает справочник категорий для Select. */
  const loadCategories = async () => {
    try {
      const categoriesData = await apiService.getCategories();
      setCategories(categoriesData);
    } catch (err) {
      console.error('Error loading categories:', err);
    }
  };

  /** Добавляет выбранные файлы в state и строит превью blob-URL. */
  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      const newImages = [...images, ...files];
      setImages(newImages);

      // Создаем превью
      const newPreviews = files.map(file => URL.createObjectURL(file));
      setImagePreviews([...imagePreviews, ...newPreviews]);
    }
  };

  /** Убирает фото по индексу из списка до отправки формы. */
  const removeImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index);
    const newPreviews = imagePreviews.filter((_, i) => i !== index);
    setImages(newImages);
    setImagePreviews(newPreviews);
  };

  /** Собирает FormData и POST на /api/ads/ с JWT, затем редирект на карточку. */
  const onSubmit = async (data: AdCreate & { category_id: number }) => {
    try {
      setLoading(true);
      setError(null);

      if (!data.category_id) {
        setError('Необходимо выбрать категорию');
        setLoading(false);
        return;
      }

      const formData = new FormData();
      formData.append('title', data.title);
      formData.append('description', data.description);
      formData.append('price', data.price.toString());
      formData.append('category_id', data.category_id.toString());
      
      if (data.location) {
        formData.append('location', data.location);
      }
      if (data.contact_phone) {
        formData.append('contact_phone', data.contact_phone);
      }
      if (data.contact_email) {
        formData.append('contact_email', data.contact_email);
      }

      // Добавляем изображения
      images.forEach((image, index) => {
        formData.append('images', image);
        if (index === 0) {
          formData.append('is_primary', 'true');
        }
      });

      // Отправляем запрос
      const response = await fetch('/api/ads/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка создания объявления');
      }

      const ad = await response.json();
      navigate(`/ads/${ad.id}`);
    } catch (err: any) {
      setError(err.message || 'Ошибка создания объявления');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Создать объявление
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <TextField
                  fullWidth
                  label="Заголовок"
                  {...register('title', { required: 'Заголовок обязателен' })}
                  error={!!errors.title}
                  helperText={errors.title?.message}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  multiline
                  rows={6}
                  label="Описание"
                  {...register('description', { required: 'Описание обязательно' })}
                  error={!!errors.description}
                  helperText={errors.description?.message}
                  margin="normal"
                />

                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Цена (₽)"
                      {...register('price', {
                        required: 'Цена обязательна',
                        min: { value: 0, message: 'Цена должна быть положительной' },
                        valueAsNumber: true,
                      })}
                      error={!!errors.price}
                      helperText={errors.price?.message}
                      margin="normal"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth margin="normal">
                      <InputLabel>Категория</InputLabel>
                      <Controller
                        name="category_id"
                        control={control}
                        rules={{ required: 'Категория обязательна' }}
                        render={({ field }) => (
                          <Select
                            {...field}
                            label="Категория"
                            error={!!errors.category_id}
                          >
                            {categories.map((category) => (
                              <MenuItem key={category.id} value={category.id}>
                                {category.name}
                              </MenuItem>
                            ))}
                          </Select>
                        )}
                      />
                      {errors.category_id && (
                        <Typography variant="caption" color="error" sx={{ mt: 0.5, ml: 1.75 }}>
                          {errors.category_id.message}
                        </Typography>
                      )}
                    </FormControl>
                  </Grid>
                </Grid>

                <TextField
                  fullWidth
                  label="Местоположение"
                  {...register('location')}
                  margin="normal"
                />
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Контактная информация
                </Typography>

                <TextField
                  fullWidth
                  label="Телефон"
                  {...register('contact_phone')}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  type="email"
                  label="Email"
                  {...register('contact_email')}
                  margin="normal"
                />
              </CardContent>
            </Card>

            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Изображения
                </Typography>

                <input
                  accept="image/*"
                  style={{ display: 'none' }}
                  id="image-upload"
                  type="file"
                  multiple
                  onChange={handleImageChange}
                />
                <label htmlFor="image-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<CloudUpload />}
                    fullWidth
                    sx={{ mb: 2 }}
                  >
                    Загрузить изображения
                  </Button>
                </label>

                {imagePreviews.length > 0 && (
                  <Grid container spacing={1}>
                    {imagePreviews.map((preview, index) => (
                      <Grid item xs={6} key={index}>
                        <Paper
                          sx={{
                            position: 'relative',
                            paddingTop: '100%',
                            backgroundImage: `url(${preview})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                          }}
                        >
                          <IconButton
                            size="small"
                            onClick={() => removeImage(index)}
                            sx={{
                              position: 'absolute',
                              top: 4,
                              right: 4,
                              bgcolor: 'rgba(255, 255, 255, 0.8)',
                            }}
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                          {index === 0 && (
                            <Chip
                              label="Основное"
                              size="small"
                              color="primary"
                              sx={{
                                position: 'absolute',
                                bottom: 4,
                                left: 4,
                              }}
                            />
                          )}
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            onClick={() => navigate('/')}
            disabled={loading}
          >
            Отмена
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <Add />}
          >
            {loading ? 'Создание...' : 'Создать объявление'}
          </Button>
        </Box>
      </form>
    </Box>
  );
};

export default AdCreatePage;

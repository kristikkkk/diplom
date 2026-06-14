/**
 * Панель администратора: очереди объявлений и отзывов, журнал решений, повтор ML.
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  Visibility,
  WarningAmber,
  Replay,
} from '@mui/icons-material';
import { Ad, Review, ModerationHistoryEntry, ApiResponse } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

/** Область содержимого вкладки MUI Tabs (показывает children только для активной вкладки). */
function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`moderation-tabpanel-${index}`}
      aria-labelledby={`moderation-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const ModerationPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [ads, setAds] = useState<Ad[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [retryingAdId, setRetryingAdId] = useState<number | null>(null);
  const [retryingReviewId, setRetryingReviewId] = useState<number | null>(null);
  const [historyData, setHistoryData] = useState<ApiResponse<ModerationHistoryEntry> | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyFilter, setHistoryFilter] = useState<'approved' | 'rejected' | ''>('');
  const [historySubjectFilter, setHistorySubjectFilter] = useState<'ad' | 'review' | ''>('');

  /** Человекочитаемый текст статуса очереди ML по объявлению/отзыву. */
  const getAiStatusLabel = (status?: string) => {
    if (status === 'checked') return 'Проверено';
    if (status === 'processing') return 'Проверяется';
    if (status === 'failed') return 'Ошибка';
    return 'В очереди на модерацию';
  };

  /** Текст вердикта по полям SFW или normalized_prediction. */
  const getAiVerdictLabel = (prediction?: string, sfw?: boolean | null) => {
    if (typeof sfw === 'boolean') {
      return sfw ? 'Контент безопасен' : 'Контент небезопасен';
    }
    if (prediction === 'approved') return 'Контент безопасен';
    if (prediction === 'rejected') return 'Контент небезопасен';
    return 'Нужна ручная проверка';
  };

  useEffect(() => {
    if (tabValue !== 2) {
      setHistoryPage(1);
      setHistoryFilter('');
      setHistorySubjectFilter('');
    }
  }, [tabValue]);

  useEffect(() => {
    if (user?.role === 'admin') {
      loadData();
    }
  }, [user, tabValue, historyPage, historyFilter, historySubjectFilter]);

  /** Загружает данные активной вкладки: очереди или историю с фильтрами пагинации. */
  const loadData = async (options?: { silent?: boolean }) => {
    try {
      if (!options?.silent) {
        setLoading(true);
      }
      setError(null);

      if (tabValue === 0) {
        const adsData = await apiService.getAds({ status: 'pending' });
        setAds(adsData.results || []);
      } else if (tabValue === 1) {
        const reviewsData = await apiService.getReviews({ status: 'pending' });
        const reviewsArray = Array.isArray(reviewsData) ? reviewsData : [];
        setReviews(reviewsArray);
      } else {
        const data = await apiService.getModerationHistory({
          page: historyPage,
          decision: historyFilter || undefined,
          subject_type: historySubjectFilter || undefined,
        });
        setHistoryData(data);
      }
    } catch (err) {
      setError('Ошибка загрузки данных');
      console.error('Error loading data:', err);
    } finally {
      if (!options?.silent) {
        setLoading(false);
      }
    }
  };

  /** Одобряет объявление или отзыв через API и обновляет списки. */
  const handleApprove = async (item: Ad | Review, type: 'ad' | 'review') => {
    try {
      if (type === 'ad') {
        await apiService.approveAd(item.id);
      } else {
        await apiService.approveReview(item.id);
      }
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка одобрения');
    }
  };

  /** Открывает диалог отклонения с выбранной сущностью. */
  const handleReject = async (item: Ad | Review, type: 'ad' | 'review') => {
    setSelectedAd(type === 'ad' ? item as Ad : null);
    setSelectedReview(type === 'review' ? item as Review : null);
    setDialogOpen(true);
  };

  /** Отправляет отклонение с причиной из состояния диалога. */
  const confirmReject = async () => {
    try {
      if (selectedAd) {
        await apiService.rejectAd(selectedAd.id, rejectReason);
      } else if (selectedReview) {
        await apiService.rejectReview(selectedReview.id, rejectReason);
      }
      setDialogOpen(false);
      setRejectReason('');
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка отклонения');
    }
  };

  /** Повторная постановка объявления в очередь ML. */
  const handleRetryModeration = async (adId: number) => {
    try {
      setRetryingAdId(adId);
      setError(null);
      await apiService.retryAdModeration(adId);
      await loadData({ silent: true });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Не удалось отправить объявление на повторную проверку');
    } finally {
      setRetryingAdId(null);
    }
  };

  /** Повторная проверка отзыва ML-сервисом. */
  const handleRetryReviewModeration = async (reviewId: number) => {
    try {
      setRetryingReviewId(reviewId);
      setError(null);
      await apiService.retryReviewModeration(reviewId);
      await loadData({ silent: true });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Не удалось отправить отзыв на повторную проверку');
    } finally {
      setRetryingReviewId(null);
    }
  };

  if (user?.role !== 'admin') {
    return (
      <Box>
        <Alert severity="error">У вас нет прав доступа к этой странице</Alert>
        <Button onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Вернуться на главную
        </Button>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em' }}>
        Moderation Center
      </Typography>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Панель модерации
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label={`Объявления на модерации (${ads.length})`} />
            <Tab label={`Отзывы на модерации (${reviews.length})`} />
            <Tab
              label={`История модерации${
                historyData != null ? ` (${historyData.count})` : ''
              }`}
            />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Заголовок</TableCell>
                    <TableCell>Автор</TableCell>
                    <TableCell>Категория</TableCell>
                    <TableCell>Проверка ИИ</TableCell>
                    <TableCell>Вердикт ИИ</TableCell>
                    <TableCell>Уверенность</TableCell>
                    <TableCell>Цена</TableCell>
                    <TableCell>Дата создания</TableCell>
                    <TableCell>Действия</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {ads.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} align="center">
                        <Typography variant="body2" color="text.secondary">
                          Нет объявлений на модерации
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    ads.map((ad) => (
                      <TableRow key={ad.id}>
                        <TableCell>{ad.id}</TableCell>
                        <TableCell>
                          <Button
                            variant="text"
                            onClick={() => navigate(`/ads/${ad.id}`)}
                          >
                            {ad.title}
                          </Button>
                        </TableCell>
                        <TableCell>{ad.author.username}</TableCell>
                        <TableCell>{ad.category.name}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.75, maxWidth: 260 }}>
                            <Chip
                              size="small"
                              label={getAiStatusLabel(ad.ai_moderation?.status)}
                              color={
                                ad.ai_moderation?.status === 'checked'
                                  ? 'success'
                                  : ad.ai_moderation?.status === 'failed'
                                  ? 'error'
                                  : 'warning'
                              }
                            />
                            {ad.ai_moderation?.status === 'failed' && ad.ai_moderation?.error ? (
                              <Typography variant="caption" color="error" sx={{ wordBreak: 'break-word' }}>
                                {ad.ai_moderation.error}
                              </Typography>
                            ) : null}
                            {ad.ai_moderation?.status === 'failed' ? (
                              <Button
                                size="small"
                                variant="outlined"
                                color="warning"
                                startIcon={
                                  retryingAdId === ad.id ? (
                                    <CircularProgress color="inherit" size={16} />
                                  ) : (
                                    <Replay fontSize="small" />
                                  )
                                }
                                disabled={retryingAdId !== null}
                                onClick={() => handleRetryModeration(ad.id)}
                              >
                                Повторить проверку ИИ
                              </Button>
                            ) : null}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {getAiVerdictLabel(
                              ad.ai_moderation?.normalized_prediction,
                              ad.ai_moderation?.verdict_sfw
                            )}
                          </Typography>
                          {ad.ai_moderation?.message && (
                            <Typography variant="caption" color="text.secondary">
                              {ad.ai_moderation.message}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {ad.ai_moderation?.confidence === null || ad.ai_moderation?.confidence === undefined ? (
                            <Typography variant="body2" color="text.secondary">
                              -
                            </Typography>
                          ) : (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Typography variant="body2">
                                {(ad.ai_moderation.confidence * 100).toFixed(1)}%
                              </Typography>
                              {ad.ai_moderation.confidence < 0.75 && (
                                <Tooltip title="Уверенность ниже 75%: ИИ сомневается">
                                  <WarningAmber color="warning" fontSize="small" />
                                </Tooltip>
                              )}
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>{ad.price.toLocaleString()} ₽</TableCell>
                        <TableCell>{new Date(ad.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          <IconButton
                            color="success"
                            onClick={() => handleApprove(ad, 'ad')}
                            title="Одобрить"
                          >
                            <CheckCircle />
                          </IconButton>
                          <IconButton
                            color="error"
                            onClick={() => handleReject(ad, 'ad')}
                            title="Отклонить"
                          >
                            <Cancel />
                          </IconButton>
                          <IconButton
                            color="primary"
                            onClick={() => navigate(`/ads/${ad.id}`)}
                            title="Просмотреть"
                          >
                            <Visibility />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Автор</TableCell>
                    <TableCell>Объявление</TableCell>
                    <TableCell>Рейтинг</TableCell>
                    <TableCell>Текст</TableCell>
                    <TableCell>Проверка ИИ</TableCell>
                    <TableCell>Вердикт ИИ</TableCell>
                    <TableCell>Уверенность</TableCell>
                    <TableCell>Дата создания</TableCell>
                    <TableCell>Действия</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reviews.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} align="center">
                        <Typography variant="body2" color="text.secondary">
                          Нет отзывов на модерации
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    reviews.map((review) => (
                      <TableRow key={review.id}>
                        <TableCell>{review.id}</TableCell>
                        <TableCell>{review.author.username}</TableCell>
                        <TableCell>
                          <Button
                            variant="text"
                            onClick={() => navigate(`/ads/${review.ad.id}`)}
                          >
                            {review.ad.title}
                          </Button>
                        </TableCell>
                        <TableCell>
                          <Chip label={review.rating} color="primary" size="small" />
                        </TableCell>
                        <TableCell sx={{ maxWidth: 200 }}>
                          {review.text.length > 50
                            ? review.text.substring(0, 50) + '...'
                            : review.text}
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.75, maxWidth: 260 }}>
                            <Chip
                              size="small"
                              label={getAiStatusLabel(review.ai_moderation?.status)}
                              color={
                                review.ai_moderation?.status === 'checked'
                                  ? 'success'
                                  : review.ai_moderation?.status === 'failed'
                                  ? 'error'
                                  : 'warning'
                              }
                            />
                            {review.ai_moderation?.status === 'failed' && review.ai_moderation?.error ? (
                              <Typography variant="caption" color="error" sx={{ wordBreak: 'break-word' }}>
                                {review.ai_moderation.error}
                              </Typography>
                            ) : null}
                            {review.ai_moderation?.status === 'failed' ? (
                              <Button
                                size="small"
                                variant="outlined"
                                color="warning"
                                startIcon={
                                  retryingReviewId === review.id ? (
                                    <CircularProgress color="inherit" size={16} />
                                  ) : (
                                    <Replay fontSize="small" />
                                  )
                                }
                                disabled={retryingReviewId !== null || retryingAdId !== null}
                                onClick={() => handleRetryReviewModeration(review.id)}
                              >
                                Повторить проверку ИИ
                              </Button>
                            ) : null}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {getAiVerdictLabel(
                              review.ai_moderation?.normalized_prediction,
                              review.ai_moderation?.verdict_sfw
                            )}
                          </Typography>
                          {review.ai_moderation?.message && (
                            <Typography variant="caption" color="text.secondary">
                              {review.ai_moderation.message}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {review.ai_moderation?.confidence === null || review.ai_moderation?.confidence === undefined ? (
                            <Typography variant="body2" color="text.secondary">
                              -
                            </Typography>
                          ) : (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Typography variant="body2">
                                {(review.ai_moderation.confidence * 100).toFixed(1)}%
                              </Typography>
                              {review.ai_moderation.confidence < 0.75 && (
                                <Tooltip title="Уверенность ниже 75%: ИИ сомневается">
                                  <WarningAmber color="warning" fontSize="small" />
                                </Tooltip>
                              )}
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>{new Date(review.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          <IconButton
                            color="success"
                            onClick={() => handleApprove(review, 'review')}
                            title="Одобрить"
                          >
                            <CheckCircle />
                          </IconButton>
                          <IconButton
                            color="error"
                            onClick={() => handleReject(review, 'review')}
                            title="Отклонить"
                          >
                            <Cancel />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel id="history-filter-label">Решение</InputLabel>
                <Select
                  labelId="history-filter-label"
                  label="Решение"
                  value={historyFilter}
                  onChange={(e) => {
                    setHistoryFilter(e.target.value as 'approved' | 'rejected' | '');
                    setHistoryPage(1);
                  }}
                >
                  <MenuItem value="">Все</MenuItem>
                  <MenuItem value="approved">Одобрено</MenuItem>
                  <MenuItem value="rejected">Отклонено</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel id="history-subject-filter-label">Тип</InputLabel>
                <Select
                  labelId="history-subject-filter-label"
                  label="Тип"
                  value={historySubjectFilter}
                  onChange={(e) => {
                    setHistorySubjectFilter(e.target.value as 'ad' | 'review' | '');
                    setHistoryPage(1);
                  }}
                >
                  <MenuItem value="">Все</MenuItem>
                  <MenuItem value="ad">Объявление</MenuItem>
                  <MenuItem value="review">Отзыв</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Дата решения</TableCell>
                    <TableCell>Тип</TableCell>
                    <TableCell>Объявление/Отзыв</TableCell>
                    <TableCell>Автор</TableCell>
                    <TableCell>Решение</TableCell>
                    <TableCell>Причина</TableCell>
                    <TableCell>Модератор</TableCell>
                    <TableCell>ИИ (на момент решения)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {!historyData?.results?.length ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography variant="body2" color="text.secondary">
                          Записей пока нет
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    historyData.results.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>
                          {new Date(row.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {row.subject_type === 'ad' ? 'Объявление' : 'Отзыв'}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 280 }}>
                          {row.subject_type === 'ad' && row.ad ? (
                            <>
                              <Button
                                variant="text"
                                onClick={() => navigate(`/ads/${row.ad!.id}`)}
                              >
                                {row.ad!.title}
                              </Button>
                              <Typography variant="caption" display="block" color="text.secondary">
                                #{row.ad!.id} · {row.ad!.status === 'approved' ? 'Одобрено' : row.ad!.status === 'rejected' ? 'Отклонено' : 'На модерации'}
                              </Typography>
                            </>
                          ) : row.review ? (
                            <>
                              <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                                {row.review.text.length > 80
                                  ? `${row.review.text.slice(0, 80)}…`
                                  : row.review.text}
                              </Typography>
                              <Typography variant="caption" display="block" color="text.secondary">
                                Отзыв #{row.review.id} · рейтинг {row.review.rating}
                              </Typography>
                              <Button
                                size="small"
                                variant="text"
                                onClick={() => navigate(`/ads/${row.review!.ad.id}`)}
                              >
                                Объявление: {row.review!.ad.title}
                              </Button>
                            </>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                        <TableCell>
                          {row.subject_type === 'ad' && row.ad
                            ? row.ad.author.username
                            : row.review
                            ? row.review.author.username
                            : '—'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={row.decision === 'approved' ? 'Одобрено' : 'Отклонено'}
                            color={row.decision === 'approved' ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell sx={{ maxWidth: 220 }}>
                          <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                            {row.reason || '—'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {row.moderator?.username ?? '—'}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 280 }}>
                          {row.ai_status || row.ai_normalized_prediction != null ? (
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                              <Typography variant="caption" color="text.secondary">
                                Статус: {row.ai_status ? getAiStatusLabel(row.ai_status) : '—'}
                              </Typography>
                              <Typography variant="body2">
                                {getAiVerdictLabel(row.ai_normalized_prediction ?? undefined, row.ai_verdict_sfw)}
                              </Typography>
                              {row.ai_confidence != null && row.ai_confidence !== undefined && (
                                <Typography variant="caption">
                                  Уверенность: {(row.ai_confidence * 100).toFixed(1)}%
                                </Typography>
                              )}
                              {row.ai_error ? (
                                <Typography variant="caption" color="error">
                                  {row.ai_error}
                                </Typography>
                              ) : null}
                            </Box>
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              —
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            {historyData && historyData.count > 0 && (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: 2,
                  mt: 2,
                }}
              >
                <Button
                  variant="outlined"
                  disabled={!historyData.previous}
                  onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                >
                  Назад
                </Button>
                <Typography variant="body2">
                  Страница {historyPage}
                  {historyData.count != null
                    ? ` · всего записей: ${historyData.count}`
                    : ''}
                </Typography>
                <Button
                  variant="outlined"
                  disabled={!historyData.next}
                  onClick={() => setHistoryPage((p) => p + 1)}
                >
                  Вперёд
                </Button>
              </Box>
            )}
          </TabPanel>
        </CardContent>
      </Card>

      {/* Диалог отклонения */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Отклонить {selectedAd ? 'объявление' : 'отзыв'}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Причина отклонения"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Отмена</Button>
          <Button onClick={confirmReject} color="error" variant="contained">
            Отклонить
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ModerationPage;

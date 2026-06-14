/**
 * HTTP-клиент к REST API бэкенда: Axios с JWT, очередью при refresh и нормализацией URL медиа.
 */
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  User, 
  Ad, 
  AdCreate, 
  Category, 
  Review, 
  MyReview,
  ReviewCreate, 
  Favorite,
  LoginData, 
  RegisterData, 
  AuthResponse,
  ApiResponse,
  ModerationHistoryEntry,
  AdFilters,
  Chat,
  Message,
  MessageCreate
} from '../types';

/** Обёртка над Axios для всех запросов к `/api`. */
class ApiService {
  private api: AxiosInstance;
  private isRefreshing = false;
  private backendOrigin: string;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (reason?: any) => void;
  }> = [];

  /**
   * Создаёт инстанс с baseURL, подставляет Bearer, настраивает refresh по 401.
   */
  constructor() {
    const envBackend = (process.env.REACT_APP_API_URL || '').replace(/\/+$/, '');
    const runtimeBackend =
      typeof window !== 'undefined' && window.location.port === '3000'
        ? `${window.location.protocol}//localhost:8000`
        : '';
    this.backendOrigin = envBackend || runtimeBackend;

    this.api = axios.create({
      baseURL: '/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Добавляем токен к каждому запросу
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Обработка ошибок авторизации с автоматическим обновлением токенов
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Если ошибка 401 и это не запрос на обновление токена
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Если уже идет обновление токена, добавляем запрос в очередь
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            })
              .then((token) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                return this.api(originalRequest);
              })
              .catch((err) => {
                return Promise.reject(err);
              });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            try {
              // Пытаемся обновить токен
              const response = await axios.post('/api/auth/token/refresh/', {
                refresh: refreshToken,
              });
              const { access } = response.data;
              localStorage.setItem('access_token', access);

              // Обновляем заголовок для оригинального запроса
              originalRequest.headers.Authorization = `Bearer ${access}`;

              // Обрабатываем очередь запросов
              this.processQueue(null, access);

              return this.api(originalRequest);
            } catch (refreshError) {
              // Если обновление токена не удалось, очищаем хранилище и перенаправляем на логин
              this.processQueue(refreshError, null);
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
              window.location.href = '/login';
              return Promise.reject(refreshError);
            } finally {
              this.isRefreshing = false;
            }
          } else {
            // Нет refresh токена, перенаправляем на логин
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * Разрешает или отклоняет запросы, ожидавшие завершения refresh токена.
   */
  private processQueue(error: any, token: string | null = null) {
    this.failedQueue.forEach((prom) => {
      if (error) {
        prom.reject(error);
      } else {
        prom.resolve(token);
      }
    });
    this.failedQueue = [];
  }

  /**
   * Преобразует относительные пути медиа и API-изображений в абсолютный URL бэкенда.
   */
  private normalizeMediaUrl(url?: string): string | undefined {
    if (!url) return url;

    try {
      const buildWithBackend = (path: string) =>
        this.backendOrigin ? `${this.backendOrigin}${path}` : path;

      if (url.startsWith('/media/')) {
        return buildWithBackend(url);
      }

      if (url.startsWith('/api/ads/image/') || url.startsWith('/api/media/image/')) {
        return buildWithBackend(url);
      }

      // Поддержка старого формата из БД: ads_images/<filename>
      if (!url.startsWith('/') && !url.includes('://')) {
        const imagePath = encodeURIComponent(url.replace(/\\/g, '/'));
        return buildWithBackend(`/api/media/image/?path=${imagePath}`);
      }

      const parsed = new URL(url);
      if (parsed.pathname.startsWith('/media/')) {
        const origin = this.backendOrigin || parsed.origin;
        return `${origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
      }
      if (parsed.pathname.startsWith('/api/ads/image/') || parsed.pathname.startsWith('/api/media/image/')) {
        const origin = this.backendOrigin || parsed.origin;
        return `${origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
      }
      return url;
    } catch {
      return url;
    }
  }

  /** Подставляет нормализованный URL аватара. */
  private normalizeUser(user: User): User {
    return {
      ...user,
      avatar: this.normalizeMediaUrl(user.avatar),
    };
  }

  /** Нормализует автора и изображения объявления для отображения на другом origin. */
  private normalizeAd(ad: Ad): Ad {
    return {
      ...ad,
      author: this.normalizeUser(ad.author),
      images: (ad.images || []).map((img) => ({
        ...img,
        image: this.normalizeMediaUrl(img.image) || img.image,
      })),
    };
  }

  // Аутентификация
  /** POST /auth/login/ — вход по email/паролю, возвращает пользователя и пару токенов. */
  async login(data: LoginData): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.api.post('/auth/login/', data);
    return response.data;
  }

  /** POST /auth/register/ — регистрация и выдача JWT. */
  async register(data: RegisterData): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.api.post('/auth/register/', data);
    return response.data;
  }

  /** GET /auth/profile/ — текущий пользователь. */
  async getProfile(): Promise<User> {
    const response: AxiosResponse<User> = await this.api.get('/auth/profile/');
    return this.normalizeUser(response.data);
  }

  /** PATCH /auth/profile/ — частичное обновление профиля. */
  async updateProfile(data: { email?: string; phone_number?: string | null }): Promise<User> {
    const response: AxiosResponse<User> = await this.api.patch('/auth/profile/', data);
    return this.normalizeUser(response.data);
  }

  // Категории
  /** GET /ads/categories/ — список активных категорий. */
  async getCategories(): Promise<Category[]> {
    const response: AxiosResponse<ApiResponse<Category> | Category[]> = await this.api.get('/ads/categories/');
    return Array.isArray(response.data) ? response.data : response.data.results;
  }

  // Объявления
  /** GET /ads/ — постраничный список с фильтрами и нормализацией вложенных данных. */
  async getAds(filters?: AdFilters): Promise<ApiResponse<Ad>> {
    const response: AxiosResponse<ApiResponse<Ad>> = await this.api.get('/ads/', {
      params: filters,
    });
    return {
      ...response.data,
      results: (response.data.results || []).map((ad) => this.normalizeAd(ad)),
    };
  }

  /** GET /ads/:id/ — одно объявление по id. */
  async getAd(id: number): Promise<Ad> {
    const response: AxiosResponse<Ad> = await this.api.get(`/ads/${id}/`);
    return this.normalizeAd(response.data);
  }

  /** POST /ads/ — создание объявления (multipart поля формы). */
  async createAd(data: AdCreate): Promise<Ad> {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value.toString());
      }
    });

    const response: AxiosResponse<Ad> = await this.api.post('/ads/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return this.normalizeAd(response.data);
  }

  /** PUT /ads/:id/ — полное обновление полей объявления. */
  async updateAd(id: number, data: Partial<AdCreate>): Promise<Ad> {
    const response: AxiosResponse<Ad> = await this.api.put(`/ads/${id}/`, data);
    return this.normalizeAd(response.data);
  }

  /** DELETE /ads/:id/ — удаление объявления. */
  async deleteAd(id: number): Promise<void> {
    await this.api.delete(`/ads/${id}/`);
  }

  /** GET /ads/recommendations/ — подборка для текущего пользователя. */
  async getRecommendations(): Promise<Ad[]> {
    const response: AxiosResponse<Ad[]> = await this.api.get('/ads/recommendations/');
    return (response.data || []).map((ad) => this.normalizeAd(ad));
  }

  // Избранное
  /** GET /ads/favorites/ — избранное с нормализованными объявлениями. */
  async getFavorites(): Promise<Favorite[]> {
    const response: AxiosResponse<Favorite[] | ApiResponse<Favorite>> = await this.api.get(
      '/ads/favorites/',
    );
    const raw = response.data;
    const list = Array.isArray(raw) ? raw : raw.results;
    return (list || []).map((favorite) => ({
      ...favorite,
      ad: this.normalizeAd(favorite.ad),
    }));
  }

  /** POST /ads/favorites/ — добавить объявление в избранное. */
  async addToFavorites(adId: number): Promise<void> {
    await this.api.post('/ads/favorites/', { ad_id: adId });
  }

  /** DELETE /ads/favorites/remove/ — убрать из избранного. */
  async removeFromFavorites(adId: number): Promise<void> {
    await this.api.delete('/ads/favorites/remove/', { data: { ad_id: adId } });
  }

  // Отзывы
  /** GET /reviews/me/ — отзывы текущего пользователя. */
  async getMyReviews(): Promise<MyReview[]> {
    const response: AxiosResponse<MyReview[] | ApiResponse<MyReview>> = await this.api.get('/reviews/me/');
    const rows = Array.isArray(response.data) ? response.data : response.data.results;
    return (rows || []).map((row) => ({
      ...row,
      ad: row.ad,
    }));
  }

  /** GET /reviews/ — список отзывов по объявлению и/или статусу. */
  async getReviews(params?: number | { ad?: number; status?: string }): Promise<Review[]> {
    const query: Record<string, string | number> = {};
    if (typeof params === 'number') {
      query.ad = params;
    } else if (params && typeof params === 'object') {
      if (params.ad != null) query.ad = params.ad;
      if (params.status != null) query.status = params.status;
    }
    const response: AxiosResponse<Review[] | ApiResponse<Review>> = await this.api.get('/reviews/', {
      params: query,
    });
    const reviews = Array.isArray(response.data) ? response.data : response.data.results;
    return (reviews || []).map((review) => ({
      ...review,
      author: this.normalizeUser(review.author),
      ad: this.normalizeAd(review.ad),
    }));
  }

  /** POST /reviews/ — создать отзыв. */
  async createReview(data: ReviewCreate): Promise<Review> {
    const response: AxiosResponse<Review> = await this.api.post('/reviews/', data);
    return {
      ...response.data,
      author: this.normalizeUser(response.data.author),
      ad: this.normalizeAd(response.data.ad),
    };
  }

  /** PUT /reviews/:id/ — изменить свой отзыв. */
  async updateReview(id: number, data: Partial<ReviewCreate>): Promise<Review> {
    const response: AxiosResponse<Review> = await this.api.put(`/reviews/${id}/`, data);
    return {
      ...response.data,
      author: this.normalizeUser(response.data.author),
      ad: this.normalizeAd(response.data.ad),
    };
  }

  /** DELETE /reviews/:id/ — удалить отзыв. */
  async deleteReview(id: number): Promise<void> {
    await this.api.delete(`/reviews/${id}/`);
  }

  // Загрузка изображений
  /** Загрузка файла изображения (если эндпоинт настроен на бэкенде). */
  async uploadImage(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('image', file);

    const response: AxiosResponse<{ url: string }> = await this.api.post('/ads/images/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.url;
  }

  // Чат
  /** GET /ads/chats/ — список чатов пользователя с сообщениями. */
  async getChats(): Promise<Chat[]> {
    const response: AxiosResponse<Chat[] | ApiResponse<Chat>> = await this.api.get('/ads/chats/');
    const chats = Array.isArray(response.data) ? response.data : response.data.results;
    return (chats || []).map((chat) => ({
      ...chat,
      ad: this.normalizeAd(chat.ad),
      tenant: this.normalizeUser(chat.tenant),
      landlord: this.normalizeUser(chat.landlord),
      messages: (chat.messages || []).map((message) => ({
        ...message,
        sender: this.normalizeUser(message.sender),
      })),
    }));
  }

  /** GET /ads/chats/:id/ — детали одного чата. */
  async getChat(chatId: number): Promise<Chat> {
    const response: AxiosResponse<Chat> = await this.api.get(`/ads/chats/${chatId}/`);
    return {
      ...response.data,
      ad: this.normalizeAd(response.data.ad),
      tenant: this.normalizeUser(response.data.tenant),
      landlord: this.normalizeUser(response.data.landlord),
      messages: (response.data.messages || []).map((message) => ({
        ...message,
        sender: this.normalizeUser(message.sender),
      })),
    };
  }

  /** POST /ads/chats/ — создать или вернуть существующий чат по объявлению. */
  async createChat(adId: number, tenantId?: number): Promise<Chat> {
    const response: AxiosResponse<Chat> = await this.api.post('/ads/chats/', {
      ad_id: adId,
      tenant_id: tenantId,
    });
    return {
      ...response.data,
      ad: this.normalizeAd(response.data.ad),
      tenant: this.normalizeUser(response.data.tenant),
      landlord: this.normalizeUser(response.data.landlord),
      messages: (response.data.messages || []).map((message) => ({
        ...message,
        sender: this.normalizeUser(message.sender),
      })),
    };
  }

  /** GET /ads/chats/:chatId/messages/ — сообщения чата. */
  async getMessages(chatId: number): Promise<Message[]> {
    const response: AxiosResponse<Message[] | ApiResponse<Message>> = await this.api.get(`/ads/chats/${chatId}/messages/`);
    const messages = Array.isArray(response.data) ? response.data : response.data.results;
    return (messages || []).map((message) => ({
      ...message,
      sender: this.normalizeUser(message.sender),
    }));
  }

  /** POST — отправить сообщение в чат. */
  async sendMessage(chatId: number, data: MessageCreate): Promise<Message> {
    const response: AxiosResponse<Message> = await this.api.post(`/ads/chats/${chatId}/messages/`, data);
    return {
      ...response.data,
      sender: this.normalizeUser(response.data.sender),
    };
  }

  /** POST /ads/chats/:chatId/read/ — отметить входящие прочитанными. */
  async markMessagesRead(chatId: number): Promise<void> {
    await this.api.post(`/ads/chats/${chatId}/read/`);
  }

  // Модерация
  /** POST /ads/:id/approve/ — одобрить объявление (модератор). */
  async approveAd(adId: number): Promise<void> {
    await this.api.post(`/ads/${adId}/approve/`);
  }

  /** POST /ads/:id/reject/ — отклонить с опциональной причиной. */
  async rejectAd(adId: number, reason?: string): Promise<void> {
    await this.api.post(`/ads/${adId}/reject/`, { reason });
  }

  /** POST /ads/:id/retry-moderation/ — повторная проверка ML. */
  async retryAdModeration(adId: number): Promise<{ message: string; queue_id: number }> {
    const response = await this.api.post<{ message: string; queue_id: number }>(
      `/ads/${adId}/retry-moderation/`,
    );
    return response.data;
  }

  /** GET /ads/moderation-history/ — журнал решений с пагинацией и фильтрами. */
  async getModerationHistory(params?: {
    page?: number;
    decision?: 'approved' | 'rejected' | '';
    subject_type?: 'ad' | 'review' | '';
  }): Promise<ApiResponse<ModerationHistoryEntry>> {
    const response = await this.api.get<ApiResponse<ModerationHistoryEntry>>(
      '/ads/moderation-history/',
      {
        params: {
          page: params?.page,
          decision: params?.decision || undefined,
          subject_type: params?.subject_type || undefined,
        },
      },
    );
    return response.data;
  }

  /** POST /reviews/:id/retry-moderation/ — повторная ML-проверка отзыва. */
  async retryReviewModeration(reviewId: number): Promise<{ message: string; queue_id: number }> {
    const response = await this.api.post<{ message: string; queue_id: number }>(
      `/reviews/${reviewId}/retry-moderation/`,
    );
    return response.data;
  }

  /** POST /reviews/:id/approve/ — одобрить отзыв. */
  async approveReview(reviewId: number): Promise<void> {
    await this.api.post(`/reviews/${reviewId}/approve/`);
  }

  /** POST /reviews/:id/reject/ — отклонить отзыв. */
  async rejectReview(reviewId: number, reason?: string): Promise<void> {
    await this.api.post(`/reviews/${reviewId}/reject/`, { reason });
  }
}

/** Единственный экземпляр клиента для всего приложения. */
export const apiService = new ApiService();

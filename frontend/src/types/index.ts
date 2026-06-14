/**
 * Общие TypeScript-типы сущностей API (пользователь, объявления, отзывы, чаты).
 */
// Типы для пользователей
export interface User {
  id: number;
  username: string;
  email: string;
  role: 'tenant' | 'landlord' | 'admin';
  avatar?: string;
  phone_number?: string;
  is_verified: boolean;
  date_joined: string;
  last_login?: string;
}

// Типы для категорий
export interface Category {
  id: number;
  name: string;
  description: string;
  icon: string;
  is_active: boolean;
}

// Типы для объявлений
export interface Ad {
  id: number;
  title: string;
  description: string;
  price: number;
  category: Category;
  author: User;
  status: 'pending' | 'approved' | 'rejected';
  location?: string;
  contact_phone?: string;
  contact_email?: string;
  is_featured: boolean;
  views_count: number;
  images: AdImage[];
  is_favorite?: boolean;
  ai_moderation?: AiModeration | null;
  created_at: string;
  updated_at: string;
  published_at?: string;
}

export interface AiModeration {
  status: 'queued' | 'processing' | 'checked' | 'failed';
  verdict_sfw: boolean | null;
  normalized_prediction: 'approved' | 'rejected' | 'pending';
  confidence: number | null;
  message: string;
  is_uncertain: boolean;
  checked_at?: string | null;
  error: string;
}

export interface AdImage {
  id: number;
  image: string;
  is_primary: boolean;
}

export interface AdCreate {
  title: string;
  description: string;
  price: number;
  category_id: number;
  location?: string;
  contact_phone?: string;
  contact_email?: string;
}

// Типы для отзывов
export interface Review {
  id: number;
  text: string;
  rating: number;
  author: User;
  ad: Ad;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
  ai_moderation?: AiModeration | null;
}

export interface ReviewCreate {
  text: string;
  rating: number;
  ad_id: number;
}

/** Отзыв пользователя на вкладке «Мои отзывы» (без полного объявления). */
export interface MyReview {
  id: number;
  text: string;
  rating: number;
  ad: Pick<Ad, 'id' | 'title'>;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
  /** Причина отклонения из журнала модерации, если статус rejected */
  moderation_rejection_reason: string;
}

// Типы для избранного
export interface Favorite {
  id: number;
  ad: Ad;
  created_at: string;
}

// Типы для аутентификации
export interface LoginData {
  email: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  role: 'tenant' | 'landlord';
  phone_number?: string;
}

export interface AuthResponse {
  user: User;
  tokens: {
    access: string;
    refresh: string;
  };
}

// Типы для API ответов
export interface ApiResponse<T> {
  results: T[];
  count: number;
  next?: string | null;
  previous?: string | null;
}

/** Фрагмент отзыва в журнале модерации. */
export interface ReviewInModerationHistory {
  id: number;
  text: string;
  rating: number;
  ad: Pick<Ad, 'id' | 'title'>;
  author: User;
}

/** Запись журнала модерации (объявление или отзыв + снимок ИИ). */
export interface ModerationHistoryEntry {
  id: number;
  subject_type: 'ad' | 'review';
  ad: (Pick<Ad, 'id' | 'title' | 'status'> & { author: User; category: Category }) | null;
  review: ReviewInModerationHistory | null;
  moderator: User | null;
  decision: 'approved' | 'rejected';
  reason: string;
  created_at: string;
  ai_status: string | null;
  ai_normalized_prediction: string | null;
  ai_confidence: number | null;
  ai_verdict_sfw: boolean | null;
  ai_message: string;
  ai_error: string;
  ai_checked_at: string | null;
}

/** @alias для обратной совместимости */
export type AdModerationHistoryEntry = ModerationHistoryEntry;

// Типы для фильтров
export interface AdFilters {
  category?: number;
  status?: string;
  is_featured?: boolean;
  search?: string;
  ordering?: string;
  min_price?: number;
  max_price?: number;
}

// Типы для чата
export interface Message {
  id: number;
  sender: User;
  text: string;
  is_read: boolean;
  created_at: string;
}

export interface Chat {
  id: number;
  ad: Ad;
  tenant: User;
  landlord: User;
  messages: Message[];
  unread_count: number;
  created_at: string;
  updated_at: string;
}

export interface MessageCreate {
  text: string;
}


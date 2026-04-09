export type UserRole = 'viewer' | 'creator' | 'admin' | 'super_admin';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  market_id?: string;
}

export interface Market {
  id: string;
  name: string;
  code: string;
  display_name: string;
  is_active: boolean;
  legal_disclaimers: LegalDisclaimer[];
}

export interface LegalDisclaimer {
  text: string;
  position: string;
  font_size: number;
  required: boolean;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  layout_config: any;
  dimensions_width: number;
  dimensions_height: number;
  safe_areas: SafeArea[];
}

export interface SafeArea {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
}

export interface GeneratedImage {
  id: string;
  prompt: string;
  status: string;
  composite_url?: string;
  layers: ImageLayer[];
  width: number;
  height: number;
  qa_score?: QAScore;
  created_at: string;
}

export interface ImageLayer {
  id: string;
  layer_index: number;
  layer_type: string;
  content_url: string;
  properties: any;
  is_editable: boolean;
}

export interface QAScore {
  overall_score: number;
  category_scores: Record<string, { score: number; weight: number; details: string[] }>;
  violations: Violation[];
  suggestions: string[];
  explanation: string;
}

export interface Violation {
  category: string;
  severity: string;
  description: string;
  recommendation: string;
}

export interface DimensionPreset {
  name: string;
  width: number;
  height: number;
  category: string;
}

export interface BrandGuideline {
  id: string;
  name: string;
  category: string;
  scope: string;
  market_id?: string;
  rules: any;
  is_active: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image_url?: string;
  image_id?: string;
  timestamp: string;
}

export interface GenerateRequest {
  prompt: string;
  width: number;
  height: number;
  market_id?: string;
  template_id?: string;
  provider?: string;
  style?: string;
  negative_prompt?: string;
}

export interface ExportRequest {
  format: 'png' | 'jpg' | 'webp' | 'pdf';
  width?: number;
  height?: number;
  quality?: number;
}

export interface ImageReview {
  approved: boolean;
  feedback?: string;
  rating?: number;
}

export interface DashboardStats {
  total_images: number;
  pending_reviews: number;
  avg_qa_score: number;
  active_templates: number;
}

export interface AuditLog {
  id: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: string;
  created_at: string;
}

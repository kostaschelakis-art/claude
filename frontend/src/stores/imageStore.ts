import { create } from 'zustand';
import type { GeneratedImage, ChatMessage, GenerateRequest } from '@/types';
import { images } from '@/api/client';

interface ImageState {
  images: GeneratedImage[];
  currentImage: GeneratedImage | null;
  isGenerating: boolean;
  chatMessages: ChatMessage[];
  generate: (request: GenerateRequest) => Promise<GeneratedImage>;
  loadImages: (params?: { skip?: number; limit?: number; status?: string }) => Promise<void>;
  setCurrentImage: (image: GeneratedImage | null) => void;
  addChatMessage: (msg: ChatMessage) => void;
  clearChat: () => void;
}

export const useImageStore = create<ImageState>((set, get) => ({
  images: [],
  currentImage: null,
  isGenerating: false,
  chatMessages: [],

  generate: async (request: GenerateRequest) => {
    set({ isGenerating: true });
    try {
      const image = await images.generate(request);
      set((state) => ({
        images: [image, ...state.images],
        currentImage: image,
        isGenerating: false,
      }));
      return image;
    } catch (error) {
      set({ isGenerating: false });
      throw error;
    }
  },

  loadImages: async (params) => {
    try {
      const imageList = await images.listImages(params);
      set({ images: imageList });
    } catch (error) {
      console.error('Failed to load images:', error);
    }
  },

  setCurrentImage: (image) => {
    set({ currentImage: image });
  },

  addChatMessage: (msg) => {
    set((state) => ({
      chatMessages: [...state.chatMessages, msg],
    }));
  },

  clearChat: () => {
    set({ chatMessages: [] });
  },
}));

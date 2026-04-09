import type { DimensionPreset } from '@/types';

export const DIMENSION_PRESETS: DimensionPreset[] = [
  // Newsletter
  { name: 'Newsletter Single', width: 600, height: 735, category: 'Newsletter' },
  { name: 'Newsletter Visual', width: 525, height: 675, category: 'Newsletter' },
  { name: 'Newsletter Double', width: 450, height: 450, category: 'Newsletter' },
  { name: 'Newsletter Half', width: 450, height: 225, category: 'Newsletter' },
  { name: 'Newsletter Quarter', width: 225, height: 300, category: 'Newsletter' },

  // CTA
  { name: 'CTA Button', width: 226, height: 65, category: 'CTA' },

  // Story
  { name: 'Story Enhanced Thumb', width: 471, height: 330, category: 'Story' },
  { name: 'Story Background', width: 1862, height: 2778, category: 'Story' },
  { name: 'Story Logo', width: 174, height: 210, category: 'Story' },
  { name: 'Story Profile Icon', width: 72, height: 72, category: 'Story' },

  // Promotional
  { name: 'Slider', width: 2048, height: 1152, category: 'Promotional' },
  { name: 'Push', width: 458, height: 258, category: 'Promotional' },
  { name: 'PM', width: 1126, height: 260, category: 'Promotional' },

  // Email
  { name: 'Email Header', width: 600, height: 200, category: 'Email' },

  // In-App
  { name: 'In-App Banner', width: 1080, height: 1920, category: 'In-App' },

  // Promo
  { name: 'Promo Banner', width: 1200, height: 628, category: 'Promo' },

  // Social
  { name: 'Social Story', width: 1080, height: 1920, category: 'Social' },
  { name: 'Social Post Square', width: 1080, height: 1080, category: 'Social' },

  // Casino
  { name: 'Casino Thumb', width: 240, height: 240, category: 'Casino' },
  { name: 'Casino Group', width: 471, height: 330, category: 'Casino' },
];

export function getPresetsByCategory(category: string): DimensionPreset[] {
  return DIMENSION_PRESETS.filter((p) => p.category === category);
}

export function getAllCategories(): string[] {
  return [...new Set(DIMENSION_PRESETS.map((p) => p.category))];
}

export function getPresetByName(name: string): DimensionPreset | undefined {
  return DIMENSION_PRESETS.find((p) => p.name === name);
}

export function groupPresetsByCategory(): Record<string, DimensionPreset[]> {
  return DIMENSION_PRESETS.reduce(
    (acc, preset) => {
      if (!acc[preset.category]) {
        acc[preset.category] = [];
      }
      acc[preset.category].push(preset);
      return acc;
    },
    {} as Record<string, DimensionPreset[]>
  );
}

import { definePreset, updatePrimaryPalette } from '@primeuix/themes'
import Nora from '@primeuix/themes/nora'

export type ColorThemeName =
  | 'indigo'
  | 'blue'
  | 'violet'
  | 'emerald'
  | 'rose'
  | 'amber'
  | 'teal'
  | 'slate'
  | 'gray'
  | 'zinc'
  | 'neutral'
  | 'stone'

export interface ColorTheme {
  name: ColorThemeName
  label: string
  /** UI上の色サークル表示用（color-500 相当の hex） */
  color: string
  palette: Record<string, string>
}

export const COLOR_THEMES: ColorTheme[] = [
  {
    name: 'indigo',
    label: 'インディゴ',
    color: '#6366f1',
    palette: {
      50: '{indigo.50}',
      100: '{indigo.100}',
      200: '{indigo.200}',
      300: '{indigo.300}',
      400: '{indigo.400}',
      500: '{indigo.500}',
      600: '{indigo.600}',
      700: '{indigo.700}',
      800: '{indigo.800}',
      900: '{indigo.900}',
      950: '{indigo.950}',
    },
  },
  {
    name: 'blue',
    label: 'ブルー',
    color: '#3b82f6',
    palette: {
      50: '{blue.50}',
      100: '{blue.100}',
      200: '{blue.200}',
      300: '{blue.300}',
      400: '{blue.400}',
      500: '{blue.500}',
      600: '{blue.600}',
      700: '{blue.700}',
      800: '{blue.800}',
      900: '{blue.900}',
      950: '{blue.950}',
    },
  },
  {
    name: 'violet',
    label: 'バイオレット',
    color: '#8b5cf6',
    palette: {
      50: '{violet.50}',
      100: '{violet.100}',
      200: '{violet.200}',
      300: '{violet.300}',
      400: '{violet.400}',
      500: '{violet.500}',
      600: '{violet.600}',
      700: '{violet.700}',
      800: '{violet.800}',
      900: '{violet.900}',
      950: '{violet.950}',
    },
  },
  {
    name: 'emerald',
    label: 'エメラルド',
    color: '#10b981',
    palette: {
      50: '{emerald.50}',
      100: '{emerald.100}',
      200: '{emerald.200}',
      300: '{emerald.300}',
      400: '{emerald.400}',
      500: '{emerald.500}',
      600: '{emerald.600}',
      700: '{emerald.700}',
      800: '{emerald.800}',
      900: '{emerald.900}',
      950: '{emerald.950}',
    },
  },
  {
    name: 'rose',
    label: 'ローズ',
    color: '#f43f5e',
    palette: {
      50: '{rose.50}',
      100: '{rose.100}',
      200: '{rose.200}',
      300: '{rose.300}',
      400: '{rose.400}',
      500: '{rose.500}',
      600: '{rose.600}',
      700: '{rose.700}',
      800: '{rose.800}',
      900: '{rose.900}',
      950: '{rose.950}',
    },
  },
  {
    name: 'amber',
    label: 'アンバー',
    color: '#f59e0b',
    palette: {
      50: '{amber.50}',
      100: '{amber.100}',
      200: '{amber.200}',
      300: '{amber.300}',
      400: '{amber.400}',
      500: '{amber.500}',
      600: '{amber.600}',
      700: '{amber.700}',
      800: '{amber.800}',
      900: '{amber.900}',
      950: '{amber.950}',
    },
  },
  {
    name: 'teal',
    label: 'ティール',
    color: '#14b8a6',
    palette: {
      50: '{teal.50}',
      100: '{teal.100}',
      200: '{teal.200}',
      300: '{teal.300}',
      400: '{teal.400}',
      500: '{teal.500}',
      600: '{teal.600}',
      700: '{teal.700}',
      800: '{teal.800}',
      900: '{teal.900}',
      950: '{teal.950}',
    },
  },
  {
    name: 'slate',
    label: 'スレート',
    color: '#64748b',
    palette: {
      50: '{slate.50}',
      100: '{slate.100}',
      200: '{slate.200}',
      300: '{slate.300}',
      400: '{slate.400}',
      500: '{slate.500}',
      600: '{slate.600}',
      700: '{slate.700}',
      800: '{slate.800}',
      900: '{slate.900}',
      950: '{slate.950}',
    },
  },
  {
    name: 'gray',
    label: 'グレー',
    color: '#6b7280',
    palette: {
      50: '{gray.50}',
      100: '{gray.100}',
      200: '{gray.200}',
      300: '{gray.300}',
      400: '{gray.400}',
      500: '{gray.500}',
      600: '{gray.600}',
      700: '{gray.700}',
      800: '{gray.800}',
      900: '{gray.900}',
      950: '{gray.950}',
    },
  },
  {
    name: 'zinc',
    label: 'ジンク',
    color: '#71717a',
    palette: {
      50: '{zinc.50}',
      100: '{zinc.100}',
      200: '{zinc.200}',
      300: '{zinc.300}',
      400: '{zinc.400}',
      500: '{zinc.500}',
      600: '{zinc.600}',
      700: '{zinc.700}',
      800: '{zinc.800}',
      900: '{zinc.900}',
      950: '{zinc.950}',
    },
  },
  {
    name: 'neutral',
    label: 'ニュートラル',
    color: '#737373',
    palette: {
      50: '{neutral.50}',
      100: '{neutral.100}',
      200: '{neutral.200}',
      300: '{neutral.300}',
      400: '{neutral.400}',
      500: '{neutral.500}',
      600: '{neutral.600}',
      700: '{neutral.700}',
      800: '{neutral.800}',
      900: '{neutral.900}',
      950: '{neutral.950}',
    },
  },
  {
    name: 'stone',
    label: 'ストーン',
    color: '#78716c',
    palette: {
      50: '{stone.50}',
      100: '{stone.100}',
      200: '{stone.200}',
      300: '{stone.300}',
      400: '{stone.400}',
      500: '{stone.500}',
      600: '{stone.600}',
      700: '{stone.700}',
      800: '{stone.800}',
      900: '{stone.900}',
      950: '{stone.950}',
    },
  },
]

/** プライマリカラーをランタイムで切り替える */
export function applyPrimaryColor(name: ColorThemeName): void {
  const theme = COLOR_THEMES.find((t) => t.name === name)
  if (theme) updatePrimaryPalette(theme.palette)
}

const defaultTheme = COLOR_THEMES.find((t) => t.name === 'indigo')!

/**
 * アプリ全体で使用する PrimeVue テーマプリセット。
 * Nora をベースに以下の点をオーバーライドしている。
 */
export const appThemePreset = definePreset(Nora, {
  semantic: {
    // プライマリカラーの初期値。ランタイムでは applyPrimaryColor() で切り替える。
    primary: defaultTheme.palette,
    // Nora + indigo のデフォルト surface は青みがかるため zinc で上書き
    surface: {
      0: '#ffffff',
      50: '{zinc.50}',
      100: '{zinc.100}',
      200: '{zinc.200}',
      300: '{zinc.300}',
      400: '{zinc.400}',
      500: '{zinc.500}',
      600: '{zinc.600}',
      700: '{zinc.700}',
      800: '{zinc.800}',
      900: '{zinc.900}',
      950: '{zinc.950}',
    },
  },
  components: {
    tabs: {
      /**
       * TabList 下部の仕切り線の色を調整。
       * Nora デフォルトは {content.border.color}（コンテンツ領域のボーダー色）だが、
       * エクスプローラーのヘッダー下線（--app-surface-border）と色を揃えるため
       * {surface.200} / {surface.700} に上書きしている。
       * --app-surface-border も同じ --p-surface-200 / --p-surface-700 を参照しており、
       * 経路は違うが最終的に同じ色が適用される。
       */
      tablist: {
        borderColor: '{surface.200}',
      },
      colorScheme: {
        dark: {
          tablist: {
            borderColor: '{surface.700}',
          },
        },
      },
    },
  },
})

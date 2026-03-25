export type ColorMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'color-mode'

export function useAppColorMode() {
  const mode = ref<ColorMode>((localStorage.getItem(STORAGE_KEY) as ColorMode) ?? 'system')

  const mq = window.matchMedia('(prefers-color-scheme: dark)')

  function apply(): void {
    const isDark =
      mode.value === 'dark' ||
      (mode.value === 'system' && mq.matches)
    document.documentElement.classList.toggle('dark', isDark)
  }

  watch(
    mode,
    (val) => {
      localStorage.setItem(STORAGE_KEY, val)
      apply()
    },
    { immediate: true },
  )

  onMounted(() => mq.addEventListener('change', apply))
  onUnmounted(() => mq.removeEventListener('change', apply))

  return { mode }
}

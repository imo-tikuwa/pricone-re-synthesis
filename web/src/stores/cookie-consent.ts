export type CookieConsentStatus = 'pending' | 'accepted' | 'declined'

export const useCookieConsentStore = defineStore(
  'cookie-consent',
  () => {
    const status = ref<CookieConsentStatus>('pending')

    function accept(): void {
      status.value = 'accepted'
    }

    function decline(): void {
      status.value = 'declined'
    }

    function reset(): void {
      status.value = 'pending'
    }

    return { status, accept, decline, reset }
  },
  {
    persist: {
      pick: ['status'],
    },
  },
)

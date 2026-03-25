const GA4_ID = import.meta.env.VITE_PRICONE_RE_SYNTHESIS_GA4_MEASUREMENT_ID as string | undefined

function loadGa4(id: string): void {
  if (document.getElementById('ga4-script')) return

  window.dataLayer = window.dataLayer ?? []
  // gtag.js は IArguments オブジェクトで判定するため arguments を使う必要がある
  window.gtag = function () {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer.push(arguments)
  }

  window.gtag('js', new Date())
  window.gtag('config', id)

  const script = document.createElement('script')
  script.id = 'ga4-script'
  script.async = true
  script.src = `https://www.googletagmanager.com/gtag/js?id=${id}`

  document.head.appendChild(script)
}

export function useGa4(): void {
  const consentStore = useCookieConsentStore()

  watch(
    () => consentStore.status,
    (status) => {
      if (status === 'accepted' && GA4_ID) {
        loadGa4(GA4_ID)
      }
    },
    { immediate: true },
  )
}

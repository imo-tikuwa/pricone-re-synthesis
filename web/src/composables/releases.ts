export interface ReleaseAsset {
  name: string
  browser_download_url: string
  download_count: number
  size: number
}

export interface Release {
  tag_name: string
  name: string
  published_at: string
  html_url: string
  assets: ReleaseAsset[]
}

export function useReleases() {
  const releases = ref<Release[]>([])
  const loading = ref(true)
  const error = ref(false)

  onMounted(async () => {
    try {
      const res = await fetch(
        'https://api.github.com/repos/imo-tikuwa/pricone-re-synthesis/releases',
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      releases.value = await res.json()
    } catch {
      error.value = true
    } finally {
      loading.value = false
    }
  })

  return { releases, loading, error }
}

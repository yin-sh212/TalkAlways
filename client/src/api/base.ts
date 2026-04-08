const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "")

export const getApiBaseURL = () => {
  const explicitBase = ((import.meta as any).env?.VITE_API_BASE_URL || "").trim()
  if (explicitBase) {
    return trimTrailingSlash(explicitBase)
  }

  if ((import.meta as any).env.DEV) {
    return "/api"
  }

  const productionBase = ((import.meta as any).env?.VITE_API_URL || "/api").trim()
  return trimTrailingSlash(productionBase || "/api")
}

export const resolveApiUrl = (endpoint: string) => {
  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`
  return `${getApiBaseURL()}${normalizedEndpoint}`
}

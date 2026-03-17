"use client"

export const SELECTED_ORGANIZATION_STORAGE_KEY = "selected_organization"
const LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY = "selectedOrganization"
const SELECTED_ORGANIZATION_EVENT = "selected-organization-change"

function safeGetItem(key: string) {
  try {
    return localStorage.getItem(key)
  } catch (error) {
    console.warn(`Failed to read localStorage key "${key}"`, error)
    return null
  }
}

function safeSetItem(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
    return true
  } catch (error) {
    console.warn(`Failed to write localStorage key "${key}"`, error)
    return false
  }
}

function safeRemoveItem(key: string) {
  try {
    localStorage.removeItem(key)
    return true
  } catch (error) {
    console.warn(`Failed to remove localStorage key "${key}"`, error)
    return false
  }
}

function readSelectedOrganization() {
  if (typeof window === "undefined") return null

  return (
    safeGetItem(SELECTED_ORGANIZATION_STORAGE_KEY) ||
    safeGetItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY)
  )
}

function writeSelectedOrganization(value: string | null) {
  if (typeof window === "undefined") return

  if (value) {
    const wrotePrimary = safeSetItem(SELECTED_ORGANIZATION_STORAGE_KEY, value)
    const wroteLegacy = safeSetItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY, value)
    return wrotePrimary && wroteLegacy
  }

  const removedPrimary = safeRemoveItem(SELECTED_ORGANIZATION_STORAGE_KEY)
  const removedLegacy = safeRemoveItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY)
  return removedPrimary && removedLegacy
}

export function getStoredSelectedOrganization(): string | null {
  return readSelectedOrganization()
}

export function setStoredSelectedOrganization(
  value: string | null,
  options: { emit?: boolean } = {}
) {
  if (typeof window === "undefined") return

  const primaryValue = safeGetItem(SELECTED_ORGANIZATION_STORAGE_KEY)
  const legacyValue = safeGetItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY)
  const currentValue = readSelectedOrganization()
  const valueChanged = currentValue !== value
  const storageAlreadySynced = value
    ? primaryValue === value && legacyValue === value
    : primaryValue === null && legacyValue === null

  if (storageAlreadySynced) {
    return
  }

  const writeSucceeded = writeSelectedOrganization(value)

  if (writeSucceeded && options.emit !== false && valueChanged) {
    window.dispatchEvent(
      new CustomEvent(SELECTED_ORGANIZATION_EVENT, {
        detail: { value },
      })
    )
  }
}

export function subscribeToSelectedOrganization(callback: (value: string | null) => void) {
  if (typeof window === "undefined") {
    return () => {}
  }

  let pendingNotification: number | null = null

  const notifyWithCurrentValue = () => {
    if (pendingNotification !== null) {
      window.clearTimeout(pendingNotification)
    }

    pendingNotification = window.setTimeout(() => {
      pendingNotification = null
      callback(getStoredSelectedOrganization())
    }, 0)
  }

  const handleStorage = (event: StorageEvent) => {
    if (
      event.key === null ||
      event.key === SELECTED_ORGANIZATION_STORAGE_KEY ||
      event.key === LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY
    ) {
      notifyWithCurrentValue()
    }
  }

  const handleCustomEvent = (event: Event) => {
    const customEvent = event as CustomEvent<{ value?: string | null }>
    callback(customEvent.detail?.value ?? getStoredSelectedOrganization())
  }

  window.addEventListener("storage", handleStorage)
  window.addEventListener(SELECTED_ORGANIZATION_EVENT, handleCustomEvent)

  return () => {
    if (pendingNotification !== null) {
      window.clearTimeout(pendingNotification)
    }
    window.removeEventListener("storage", handleStorage)
    window.removeEventListener(SELECTED_ORGANIZATION_EVENT, handleCustomEvent)
  }
}

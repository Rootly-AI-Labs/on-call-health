/**
 * Z-Index Scale for layering components
 * Based on: https://www.smashingmagazine.com/2021/02/css-z-index-component-based-web-applications/
 */
export const Z_INDEX = {
  BASE: 0,
  DROPDOWN: 10,
  STICKY: 20,
  FIXED: 30,
  MODAL_BACKDROP: 40,
  MODAL: 50,
  DRAWER: 50,      // Sheet components
  DIALOG: 60,      // Dialog components (above drawers)
  POPOVER: 70,
  TOOLTIP: 80,
  NOTIFICATION: 90,
  SUPREME: 100     // Absolutely must be on top
} as const

export type ZIndex = typeof Z_INDEX[keyof typeof Z_INDEX]

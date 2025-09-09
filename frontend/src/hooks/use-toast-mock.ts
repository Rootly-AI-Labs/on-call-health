/**
 * Mock toast hook for debugging
 */

export function useToast() {
  return {
    toast: (options: any) => {
      
    },
    toasts: [],
    dismiss: (id?: string) => {
      
    }
  };
}
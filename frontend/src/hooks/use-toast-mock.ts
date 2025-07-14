/**
 * Mock toast hook for debugging
 */

export function useToast() {
  return {
    toast: (options: any) => {
      console.log('Mock toast:', options);
    },
    toasts: [],
    dismiss: (id?: string) => {
      console.log('Mock dismiss:', id);
    }
  };
}
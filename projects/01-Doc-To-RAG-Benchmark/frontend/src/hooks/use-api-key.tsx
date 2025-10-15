import { create } from "zustand";

type ApiKeyState = {
  apiKey: string;
  setApiKey: (value: string) => void;
};

export const useApiKeyStore = create<ApiKeyState>((set) => ({
  apiKey: "",
  setApiKey: (value: string) => set({ apiKey: value }),
}));

export const useApiKey = () => useApiKeyStore();

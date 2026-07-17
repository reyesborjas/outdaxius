import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@tokens": path.resolve(__dirname, "src/tokens.css"),
      "@": path.resolve(__dirname, "src"), // optional, for all src imports
    },
  },
});

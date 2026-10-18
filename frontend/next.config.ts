import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // static site: no server needed, deployable to GitHub Pages / Vercel
  reactCompiler: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

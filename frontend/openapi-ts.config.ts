import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: 'http://localhost:8000/openapi.json',
  output: {
    path: 'src/api/generated',
    clean: true,
  },
  plugins: [
    {
      name: '@hey-api/client-fetch',
      bundle: true,
      runtimeConfigPath: '../client',
    },
    '@tanstack/react-query',
  ],
})

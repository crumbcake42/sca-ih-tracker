import type { Preview, Decorator } from '@storybook/react-vite'
import { QueryClientProvider } from '@tanstack/react-query'
import { createTestQueryClient } from '../src/test/queryClient'
import '../src/styles.css'

/** Wrap every story in a fresh QueryClient (retries off, no cache). */
const withQueryClient: Decorator = (Story) => {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      <Story />
    </QueryClientProvider>
  )
}

const preview: Preview = {
  decorators: [withQueryClient],
  parameters: {
    layout: 'padded',
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: 'todo',
    },
  },
}

export default preview

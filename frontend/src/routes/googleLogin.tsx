import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/googleLogin')({
  component: () => <div>Hello /googleLogin!</div>
})
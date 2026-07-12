import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { Login } from '../Login'
import { AuthProvider } from '../../context/AuthContext'
import * as authApi from '../../api/auth'

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  it('shows an error on invalid credentials', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValueOnce(new Error('unauthorized'))
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'nobody@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
    })
  })

  it('calls the login API with entered credentials', async () => {
    const loginSpy = vi.spyOn(authApi, 'login').mockResolvedValueOnce('fake-token')
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'demo@openoncall.local')
    await user.type(screen.getByLabelText('Password'), 'demopass123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith('demo@openoncall.local', 'demopass123')
    })
  })
})

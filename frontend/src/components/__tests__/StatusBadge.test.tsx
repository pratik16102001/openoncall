import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusBadge } from '../StatusBadge'

describe('StatusBadge', () => {
  it('renders the triggered status', () => {
    render(<StatusBadge status="triggered" />)
    expect(screen.getByText('triggered')).toBeInTheDocument()
  })

  it('renders the resolved status', () => {
    render(<StatusBadge status="resolved" />)
    expect(screen.getByText('resolved')).toBeInTheDocument()
  })
})

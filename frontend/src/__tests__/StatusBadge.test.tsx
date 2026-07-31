import { render, screen } from '@testing-library/react';
import StatusBadge from '@/components/StatusBadge';

describe('StatusBadge', () => {
  it('renders status text', () => {
    render(<StatusBadge status="deployed" />);
    expect(screen.getByText('deployed')).toBeInTheDocument();
  });

  it('applies success styles for deployed', () => {
    render(<StatusBadge status="deployed" />);
    const badge = screen.getByText('deployed');
    expect(badge.className).toContain('green');
  });

  it('applies warning styles for training', () => {
    render(<StatusBadge status="training" />);
    const badge = screen.getByText('training');
    expect(badge.className).toContain('yellow');
  });

  it('applies error styles for failed', () => {
    render(<StatusBadge status="failed" />);
    const badge = screen.getByText('failed');
    expect(badge.className).toContain('red');
  });

  it('applies info styles for trained', () => {
    render(<StatusBadge status="trained" />);
    const badge = screen.getByText('trained');
    expect(badge.className).toContain('blue');
  });

  it('applies success styles for completed', () => {
    render(<StatusBadge status="completed" />);
    const badge = screen.getByText('completed');
    expect(badge.className).toContain('green');
  });

  it('applies neutral styles for unknown status', () => {
    render(<StatusBadge status="unknown_status" />);
    const badge = screen.getByText('unknown_status');
    expect(badge.className).toContain('gray');
  });
});

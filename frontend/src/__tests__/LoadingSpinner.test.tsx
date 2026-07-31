import { render } from '@testing-library/react';
import LoadingSpinner from '@/components/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default size', () => {
    const { container } = render(<LoadingSpinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain('h-8 w-8');
  });

  it('renders with small size', () => {
    const { container } = render(<LoadingSpinner size="sm" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain('h-4 w-4');
  });

  it('renders with large size', () => {
    const { container } = render(<LoadingSpinner size="lg" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain('h-12 w-12');
  });

  it('applies custom className', () => {
    const { container } = render(<LoadingSpinner className="mt-10" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain('mt-10');
  });

  it('has animate-spin class', () => {
    const { container } = render(<LoadingSpinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain('animate-spin');
  });
});

import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from '@/components/Pagination';

describe('Pagination', () => {
  it('renders nothing when totalPages <= 1', () => {
    const { container } = render(<Pagination currentPage={1} totalPages={1} onPageChange={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders page buttons', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('highlights current page', () => {
    render(<Pagination currentPage={3} totalPages={5} onPageChange={() => {}} />);
    const currentPageBtn = screen.getByText('3');
    expect(currentPageBtn.className).toContain('bg-primary-600');
  });

  it('calls onPageChange when clicking a page', () => {
    const handleChange = jest.fn();
    render(<Pagination currentPage={1} totalPages={5} onPageChange={handleChange} />);
    fireEvent.click(screen.getByText('3'));
    expect(handleChange).toHaveBeenCalledWith(3);
  });

  it('disables previous button on first page', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);
    const prevButton = screen.getAllByRole('button')[0];
    expect(prevButton).toBeDisabled();
  });

  it('disables next button on last page', () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />);
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons[buttons.length - 1];
    expect(nextButton).toBeDisabled();
  });

  it('shows ellipsis for large page counts', () => {
    render(<Pagination currentPage={5} totalPages={20} onPageChange={() => {}} />);
    expect(screen.getByText('...')).toBeInTheDocument();
  });
});

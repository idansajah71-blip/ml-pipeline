import { render, screen, fireEvent } from '@testing-library/react';
import SearchInput from '@/components/SearchInput';

describe('SearchInput', () => {
  it('renders with placeholder', () => {
    render(<SearchInput value="" onChange={() => {}} placeholder="Search models..." />);
    expect(screen.getByPlaceholderText('Search models...')).toBeInTheDocument();
  });

  it('renders default placeholder', () => {
    render(<SearchInput value="" onChange={() => {}} />);
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
  });

  it('displays current value', () => {
    render(<SearchInput value="hello" onChange={() => {}} />);
    expect(screen.getByDisplayValue('hello')).toBeInTheDocument();
  });

  it('calls onChange when typing', () => {
    const handleChange = jest.fn();
    render(<SearchInput value="" onChange={handleChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } });
    expect(handleChange).toHaveBeenCalledWith('test');
  });

  it('shows clear button when value is not empty', () => {
    render(<SearchInput value="hello" onChange={() => {}} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('does not show clear button when value is empty', () => {
    const { container } = render(<SearchInput value="" onChange={() => {}} />);
    expect(container.querySelector('button')).toBeNull();
  });

  it('clears value when clicking clear button', () => {
    const handleChange = jest.fn();
    render(<SearchInput value="hello" onChange={handleChange} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleChange).toHaveBeenCalledWith('');
  });
});

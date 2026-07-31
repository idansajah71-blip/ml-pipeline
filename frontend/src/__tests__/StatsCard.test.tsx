import { render, screen } from '@testing-library/react';
import StatsCard from '@/components/StatsCard';
import { Brain } from 'lucide-react';

describe('StatsCard', () => {
  it('renders title and value', () => {
    render(<StatsCard title="Total Models" value={42} icon={Brain} />);
    expect(screen.getByText('Total Models')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders string value', () => {
    render(<StatsCard title="Status" value="Active" icon={Brain} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders change text with positive type', () => {
    render(<StatsCard title="Models" value={10} icon={Brain} change="+5 from last month" changeType="positive" />);
    expect(screen.getByText('+5 from last month')).toBeInTheDocument();
  });

  it('renders change text with negative type', () => {
    render(<StatsCard title="Models" value={10} icon={Brain} change="-2 from last month" changeType="negative" />);
    expect(screen.getByText('-2 from last month')).toBeInTheDocument();
  });

  it('does not render change when not provided', () => {
    const { container } = render(<StatsCard title="Models" value={10} icon={Brain} />);
    expect(container.querySelector('.text-green-600')).toBeNull();
    expect(container.querySelector('.text-red-600')).toBeNull();
  });
});

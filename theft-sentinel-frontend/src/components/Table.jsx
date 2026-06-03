import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';

const Table = ({ columns, data, onRowClick, loading }) => {
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-12 bg-dark-card rounded mb-4 border border-dark-border"></div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-dark-surface rounded mb-2 border border-dark-border"></div>
        ))}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-dark-text-muted text-lg">No data available</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto shadow-md rounded-lg border border-dark-border -mx-1 sm:mx-0">
      <table className="min-w-[720px] w-full divide-y divide-dark-border">
        <thead className="bg-dark-surface">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-6 py-3 text-left text-xs font-medium text-dark-text-primary uppercase tracking-wider"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-dark-card divide-y divide-dark-border">
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              onClick={() => onRowClick && onRowClick(row)}
              className={onRowClick ? 'hover:bg-dark-surface cursor-pointer transition-colors' : ''}
            >
              {columns.map((column) => (
                <td key={column.key} className="px-6 py-4 whitespace-nowrap text-sm text-dark-text-primary">
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const Pagination = ({ currentPage, totalPages, onPageChange }) => {
  const pages = [];
  const maxVisible = 5;
  
  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  let endPage = Math.min(totalPages, startPage + maxVisible - 1);
  
  if (endPage - startPage + 1 < maxVisible) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    pages.push(i);
  }

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-6">
      <div className="text-sm text-dark-text-secondary">
        Page {currentPage} of {totalPages}
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-2 bg-dark-surface text-dark-text-primary rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-dark-card transition-colors border border-dark-border"
        >
          <ChevronLeftIcon className="h-5 w-5" />
        </button>
        
        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`px-4 py-2 rounded-md transition-colors border ${
              page === currentPage
                ? 'bg-ai-blue text-white border-ai-blue'
                : 'bg-dark-card text-dark-text-primary border-dark-border hover:bg-dark-surface'
            }`}
          >
            {page}
          </button>
        ))}
        
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-2 bg-dark-surface text-dark-text-primary rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-dark-card transition-colors border border-dark-border"
        >
          <ChevronRightIcon className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
};

export default Table;


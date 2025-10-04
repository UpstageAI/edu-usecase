'use client';

import { useState, useMemo } from 'react';

interface DataTableProps {
  data: any[];
  title?: string;
  pageSize?: number;
  searchable?: boolean;
  sortable?: boolean;
  className?: string;
}

export function DataTable({
  data,
  title,
  pageSize = 10,
  searchable = true,
  sortable = true,
  className = ''
}: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const [sortConfig, setSortConfig] = useState<{
    key: string | null;
    direction: 'asc' | 'desc';
  }>({ key: null, direction: 'asc' });

  // Get columns from first data item
  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];
    return Object.keys(data[0]);
  }, [data]);

  // Filter data based on search term
  const filteredData = useMemo(() => {
    if (!searchTerm) return data;
    return data.filter((row) =>
      Object.values(row).some((value) =>
        String(value).toLowerCase().includes(searchTerm.toLowerCase())
      )
    );
  }, [data, searchTerm]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortConfig.key) return filteredData;

    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key!];
      const bVal = b[sortConfig.key!];

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortConfig]);

  // Paginate data
  const paginatedData = useMemo(() => {
    const start = currentPage * pageSize;
    const end = start + pageSize;
    return sortedData.slice(start, end);
  }, [sortedData, currentPage, pageSize]);

  const totalPages = Math.ceil(sortedData.length / pageSize);

  const handleSort = (key: string) => {
    if (!sortable) return;

    setSortConfig((prev) => ({
      key,
      direction:
        prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  if (!data || data.length === 0) {
    return (
      <div className={className}>
        <p style={{ textAlign: 'center', padding: '20px', color: '#64748b' }}>
          No data available
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      {title && (
        <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '600' }}>
          {title}
        </h3>
      )}

      {searchable && (
        <div style={{ marginBottom: '12px' }}>
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(0);
            }}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              fontSize: '14px',
            }}
          />
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {columns.map((column) => (
                <th
                  key={column}
                  onClick={() => handleSort(column)}
                  style={{
                    padding: '12px',
                    textAlign: 'left',
                    fontWeight: '600',
                    fontSize: '14px',
                    cursor: sortable ? 'pointer' : 'default',
                    userSelect: 'none',
                  }}
                >
                  {column}
                  {sortConfig.key === column && (
                    <span style={{ marginLeft: '4px' }}>
                      {sortConfig.direction === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, idx) => (
              <tr
                key={idx}
                style={{
                  borderBottom: '1px solid #e5e7eb',
                }}
              >
                {columns.map((column) => (
                  <td
                    key={column}
                    style={{
                      padding: '12px',
                      fontSize: '14px',
                    }}
                  >
                    {String(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div
          style={{
            marginTop: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: '14px', color: '#64748b' }}>
            Page {currentPage + 1} of {totalPages}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              style={{
                padding: '6px 12px',
                border: '1px solid #e5e7eb',
                borderRadius: '4px',
                background: 'white',
                cursor: currentPage === 0 ? 'not-allowed' : 'pointer',
                opacity: currentPage === 0 ? 0.5 : 1,
              }}
            >
              Previous
            </button>
            <button
              onClick={() =>
                setCurrentPage((p) => Math.min(totalPages - 1, p + 1))
              }
              disabled={currentPage === totalPages - 1}
              style={{
                padding: '6px 12px',
                border: '1px solid #e5e7eb',
                borderRadius: '4px',
                background: 'white',
                cursor: currentPage === totalPages - 1 ? 'not-allowed' : 'pointer',
                opacity: currentPage === totalPages - 1 ? 0.5 : 1,
              }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

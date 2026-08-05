'use client';

import { useState, useCallback } from 'react';
import { Upload, File, X } from 'lucide-react';
import clsx from 'clsx';

interface DragDropUploadProps {
  accept?: string;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export default function DragDropUpload({ accept = '.csv,.tsv,.xls,.xlsx,.json,.ods', onFileSelect, disabled }: DragDropUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const processFile = useCallback((file: File) => {
    setSelectedFile(file);
    onFileSelect(file);
    setIsDragging(false);
  }, [onFileSelect]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  }, [disabled, processFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }, [processFile]);

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    onFileSelect(null);
  }, [onFileSelect]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={clsx(
        'relative rounded-lg border-2 border-dashed p-6 text-center transition-colors',
        disabled && 'opacity-50 cursor-not-allowed',
        isDragging
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
          : selectedFile
          ? 'border-green-300 bg-green-50 dark:bg-green-900/20'
          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
      )}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleFileInput}
        disabled={disabled}
        className="absolute inset-0 cursor-pointer opacity-0"
      />

      {selectedFile ? (
        <div className="flex items-center justify-center gap-3">
          <File className="h-8 w-8 text-green-600" />
          <div className="text-left">
            <p className="text-sm font-medium text-gray-900 dark:text-white">{selectedFile.name}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{formatSize(selectedFile.size)}</p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); clearFile(); }}
            className="ml-2 rounded-full p-1 hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>
      ) : (
        <>
          <Upload className="mx-auto mb-2 h-8 w-8 text-gray-400" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium text-primary-600">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500">CSV, TSV, JSON, XLS, XLSX, ODS</p>
        </>
      )}
    </div>
  );
}

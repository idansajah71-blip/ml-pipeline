import { useState, useCallback } from 'react';

export interface ValidationRules {
  [field: string]: {
    required?: boolean;
    minLength?: number;
    maxLength?: number;
    pattern?: RegExp;
    custom?: (value: any) => string | null;
  };
}

export interface ValidationErrors {
  [field: string]: string;
}

export function useFormValidation(rules: ValidationRules) {
  const [errors, setErrors] = useState<ValidationErrors>({});

  const validate = useCallback(
    (data: Record<string, any>): boolean => {
      const newErrors: ValidationErrors = {};

      for (const [field, rule] of Object.entries(rules)) {
        const value = data[field];

        if (rule.required && (!value || (typeof value === 'string' && value.trim() === ''))) {
          newErrors[field] = `${field.replace(/_/g, ' ')} is required`;
          continue;
        }

        if (value && rule.minLength && String(value).length < rule.minLength) {
          newErrors[field] = `${field.replace(/_/g, ' ')} must be at least ${rule.minLength} characters`;
          continue;
        }

        if (value && rule.maxLength && String(value).length > rule.maxLength) {
          newErrors[field] = `${field.replace(/_/g, ' ')} must be at most ${rule.maxLength} characters`;
          continue;
        }

        if (value && rule.pattern && !rule.pattern.test(String(value))) {
          newErrors[field] = `${field.replace(/_/g, ' ')} format is invalid`;
          continue;
        }

        if (rule.custom) {
          const customError = rule.custom(value);
          if (customError) {
            newErrors[field] = customError;
          }
        }
      }

      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    },
    [rules]
  );

  const clearErrors = useCallback(() => setErrors({}), []);

  const clearFieldError = useCallback((field: string) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  return { errors, validate, clearErrors, clearFieldError };
}

export function FormField({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

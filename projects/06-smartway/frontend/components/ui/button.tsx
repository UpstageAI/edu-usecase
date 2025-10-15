'use client';

import * as React from 'react';

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const baseStyles = {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '6px',
      fontSize: '14px',
      fontWeight: '500',
      transition: 'all 0.2s',
      cursor: 'pointer',
      border: 'none',
      outline: 'none',
    };

    const variantStyles = {
      default: {
        background: '#3b82f6',
        color: 'white',
      },
      outline: {
        background: 'transparent',
        border: '1px solid #e5e7eb',
        color: '#1f2937',
      },
      ghost: {
        background: 'transparent',
        color: '#1f2937',
      },
    };

    const sizeStyles = {
      default: {
        padding: '8px 16px',
      },
      sm: {
        padding: '6px 12px',
        fontSize: '12px',
      },
      lg: {
        padding: '12px 24px',
        fontSize: '16px',
      },
    };

    const styles = {
      ...baseStyles,
      ...variantStyles[variant],
      ...sizeStyles[size],
    };

    return <button ref={ref} style={styles} {...props} />;
  }
);

Button.displayName = 'Button';

export { Button };

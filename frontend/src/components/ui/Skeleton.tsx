interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circle' | 'rect';
  className?: string;
}

export function Skeleton({ 
  width = '100%', 
  height = '1rem', 
  variant = 'text',
  className = ''
}: SkeletonProps) {
  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div 
      className={`skeleton skeleton-${variant} ${className}`}
      style={style}
    />
  );
}

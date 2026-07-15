import { Loader2 } from 'lucide-react';

const LoadingSpinner = ({
  message = 'Loading...',
  size = 'default',
  fullScreen = false,
  className = ''
}) => {
  const sizeClasses = {
    small: 'h-5 w-5',
    default: 'h-8 w-8',
    large: 'h-12 w-12',
  };

  const spinnerSize = sizeClasses[size] || sizeClasses.default;

  const content = (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <Loader2 className={`${spinnerSize} animate-spin text-accent-cyan`} />
      {message && (
        <span className="text-forensic-400 text-sm font-medium">{message}</span>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-forensic-950">
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center py-12">
      {content}
    </div>
  );
};

export default LoadingSpinner;
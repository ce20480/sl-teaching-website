import { useState, useEffect, useRef } from "react";
import { X, ZoomIn, ZoomOut, RotateCw } from "lucide-react";

interface ImagePreviewProps {
  file: File;
  onRemove: () => void;
  className?: string;
  landmarks?: number[];
}

export function ImagePreview({
  file,
  onRemove,
  className = "",
  landmarks,
}: ImagePreviewProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [imageDimensions, setImageDimensions] = useState({
    width: 0,
    height: 0,
  });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // Create preview URL for the image
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    // Clean up the URL when component unmounts
    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [file]);

  // Draw landmarks on canvas when they change or when image loads
  useEffect(() => {
    if (
      !landmarks ||
      !previewUrl ||
      !canvasRef.current ||
      !imageRef.current ||
      !imageRef.current.complete
    ) {
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = imageRef.current;
    const container = img.parentElement;
    if (!container) return;

    // Get the actual displayed dimensions of the image
    const imgRect = img.getBoundingClientRect();
    const displayedWidth = imgRect.width / zoom; // Account for zoom
    const displayedHeight = imgRect.height / zoom;

    // Set canvas to match container size
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    // Calculate scale factors between original image and displayed size
    const scaleX = displayedWidth / img.naturalWidth;
    const scaleY = displayedHeight / img.naturalHeight;

    // Calculate offset to center landmarks
    const offsetX = (canvas.width - displayedWidth) / 2;
    const offsetY = (canvas.height - displayedHeight) / 2;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Save context for transformations
    ctx.save();

    // Move to center for rotation
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.translate(-canvas.width / 2, -canvas.height / 2);

    // Convert normalized landmarks to display coordinates
    const points: [number, number][] = [];
    for (let i = 0; i < landmarks.length; i += 3) {
      // Convert from normalized [0,1] to actual pixels on displayed image
      const x = landmarks[i] * img.naturalWidth * scaleX + offsetX;
      const y = landmarks[i + 1] * img.naturalHeight * scaleY + offsetY;
      points.push([x, y]);
    }

    // Draw connections (hand skeleton)
    // Define connections based on MediaPipe hand landmark model
    const connections = [
      // Thumb
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      // Index finger
      [0, 5],
      [5, 6],
      [6, 7],
      [7, 8],
      // Middle finger
      [0, 9],
      [9, 10],
      [10, 11],
      [11, 12],
      // Ring finger
      [0, 13],
      [13, 14],
      [14, 15],
      [15, 16],
      // Pinky
      [0, 17],
      [17, 18],
      [18, 19],
      [19, 20],
      // Palm
      [0, 5],
      [5, 9],
      [9, 13],
      [13, 17],
    ];

    // Draw lines
    ctx.strokeStyle = "rgba(0, 120, 255, 0.8)";
    ctx.lineWidth = Math.max(2 * scaleX, 1.5); // Scale line width proportionally, with minimum thickness
    connections.forEach(([i, j]) => {
      if (i < points.length && j < points.length) {
        ctx.beginPath();
        ctx.moveTo(points[i][0], points[i][1]);
        ctx.lineTo(points[j][0], points[j][1]);
        ctx.stroke();
      }
    });

    // Draw points
    points.forEach(([x, y], i) => {
      ctx.beginPath();
      // Different color for fingertips and wrist
      if (i === 0) {
        // Wrist point
        ctx.fillStyle = "rgba(255, 100, 100, 0.9)";
        ctx.arc(x, y, Math.max(5 * scaleX, 3), 0, 2 * Math.PI);
      } else if ([4, 8, 12, 16, 20].includes(i)) {
        // Fingertips
        ctx.fillStyle = "rgba(255, 0, 0, 0.9)";
        ctx.arc(x, y, Math.max(4 * scaleX, 2.5), 0, 2 * Math.PI);
      } else {
        // Other joints
        ctx.fillStyle = "rgba(0, 200, 255, 0.9)";
        ctx.arc(x, y, Math.max(3 * scaleX, 2), 0, 2 * Math.PI);
      }
      ctx.fill();
    });

    // Restore context
    ctx.restore();
  }, [landmarks, previewUrl, imageDimensions, zoom, rotation]);

  // Update image dimensions when the image loads
  const handleImageLoad = () => {
    if (imageRef.current) {
      setImageDimensions({
        width: imageRef.current.width,
        height: imageRef.current.height,
      });
    }
  };

  if (!previewUrl) {
    return (
      <div className="flex items-center justify-center h-32">
        Loading preview...
      </div>
    );
  }

  const handleZoomIn = (e: React.MouseEvent) => {
    e.stopPropagation();
    setZoom((prev) => Math.min(prev + 0.25, 2.5));
  };

  const handleZoomOut = (e: React.MouseEvent) => {
    e.stopPropagation();
    setZoom((prev) => Math.max(prev - 0.25, 0.5));
  };

  const handleRotate = (e: React.MouseEvent) => {
    e.stopPropagation();
    setRotation((prev) => (prev + 90) % 360);
  };

  return (
    <div
      className={`relative rounded-lg overflow-hidden border border-gray-200 ${className}`}
    >
      <div className="absolute top-2 right-2 z-10 flex gap-1">
        <button
          onClick={handleZoomIn}
          className="p-1 bg-white/90 rounded-full shadow hover:bg-gray-100"
          title="Zoom in"
        >
          <ZoomIn className="h-4 w-4 text-gray-700" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1 bg-white/90 rounded-full shadow hover:bg-gray-100"
          title="Zoom out"
        >
          <ZoomOut className="h-4 w-4 text-gray-700" />
        </button>
        <button
          onClick={handleRotate}
          className="p-1 bg-white/90 rounded-full shadow hover:bg-gray-100"
          title="Rotate"
        >
          <RotateCw className="h-4 w-4 text-gray-700" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="p-1 bg-white/90 rounded-full shadow hover:bg-red-100"
          title="Remove"
        >
          <X className="h-4 w-4 text-red-500" />
        </button>
      </div>

      <div className="h-64 flex items-center justify-center bg-gray-50 overflow-hidden relative">
        <img
          ref={imageRef}
          src={previewUrl}
          alt={file.name}
          className="max-w-full max-h-full object-contain transition-all duration-200"
          style={{
            transform: `scale(${zoom}) rotate(${rotation}deg)`,
            transformOrigin: "center",
          }}
          onLoad={handleImageLoad}
        />

        {/* Canvas overlay for landmarks */}
        {landmarks && landmarks.length > 0 && (
          <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
            }}
          />
        )}
      </div>

      <div className="p-2 bg-gray-50 text-xs text-gray-600 truncate border-t border-gray-200 flex justify-between">
        <span>
          {file.name} ({(file.size / 1024).toFixed(1)} KB)
        </span>
        {landmarks && landmarks.length > 0 && (
          <span className="text-blue-600">Hand landmarks detected</span>
        )}
      </div>
    </div>
  );
}

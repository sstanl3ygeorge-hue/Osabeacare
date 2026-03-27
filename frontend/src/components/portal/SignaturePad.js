import { useState, useRef, useEffect } from 'react';
import SignatureCanvas from 'react-signature-canvas';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { PenLine, Type, Eraser, Check } from 'lucide-react';

export default function SignaturePad({ 
  label = "Signature",
  value = null,
  onChange,
  disabled = false,
  required = false,
  showDate = true,
  className = ""
}) {
  const [mode, setMode] = useState('type'); // 'type' or 'draw'
  const [typedSignature, setTypedSignature] = useState(value?.typed || '');
  const [signatureData, setSignatureData] = useState(value?.drawn || null);
  const [signedDate, setSignedDate] = useState(value?.date || '');
  const sigCanvas = useRef(null);

  useEffect(() => {
    if (value) {
      if (value.typed) setTypedSignature(value.typed);
      if (value.drawn) setSignatureData(value.drawn);
      if (value.date) setSignedDate(value.date);
    }
  }, [value]);

  const handleClear = () => {
    if (mode === 'draw' && sigCanvas.current) {
      sigCanvas.current.clear();
      setSignatureData(null);
    } else {
      setTypedSignature('');
    }
    updateValue(null, null, signedDate);
  };

  const handleDrawEnd = () => {
    if (sigCanvas.current && !sigCanvas.current.isEmpty()) {
      const data = sigCanvas.current.toDataURL('image/png');
      setSignatureData(data);
      updateValue(typedSignature, data, signedDate);
    }
  };

  const handleTypedChange = (e) => {
    const newTyped = e.target.value;
    setTypedSignature(newTyped);
    updateValue(newTyped, signatureData, signedDate);
  };

  const handleDateChange = (e) => {
    const newDate = e.target.value;
    setSignedDate(newDate);
    updateValue(typedSignature, signatureData, newDate);
  };

  const updateValue = (typed, drawn, date) => {
    if (onChange) {
      const hasSignature = (typed && typed.trim()) || drawn;
      onChange({
        typed: typed || '',
        drawn: drawn || null,
        date: date || new Date().toISOString().split('T')[0],
        hasSignature,
        displayValue: typed || (drawn ? '[Drawn Signature]' : '')
      });
    }
  };

  const handleConfirm = () => {
    const currentDate = signedDate || new Date().toISOString().split('T')[0];
    setSignedDate(currentDate);
    updateValue(typedSignature, signatureData, currentDate);
  };

  // Load existing drawn signature into canvas
  useEffect(() => {
    if (mode === 'draw' && signatureData && sigCanvas.current) {
      const img = new Image();
      img.onload = () => {
        const canvas = sigCanvas.current.getCanvas();
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
      };
      img.src = signatureData;
    }
  }, [mode, signatureData]);

  if (disabled && value?.hasSignature) {
    return (
      <div className={`space-y-2 ${className}`}>
        <Label>{label}</Label>
        <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
          {value.drawn ? (
            <img src={value.drawn} alt="Signature" className="max-h-20 border-b border-dashed border-text-muted" />
          ) : (
            <p className="font-signature text-2xl text-text-primary italic">{value.typed}</p>
          )}
          {value.date && (
            <p className="text-xs text-text-muted mt-2">Signed: {new Date(value.date).toLocaleDateString()}</p>
          )}
        </div>
      </div>
    );
  }

  if (disabled) {
    return (
      <div className={`space-y-2 ${className}`}>
        <Label>{label}</Label>
        <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] text-text-muted text-sm">
          Awaiting signature
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`} data-testid="signature-pad">
      <Label>
        {label}
        {required && <span className="text-error ml-1">*</span>}
      </Label>

      <Tabs value={mode} onValueChange={setMode} className="w-full">
        <TabsList className="bg-[#F8FAFA] border border-[#E4E8EB] p-1 rounded-xl w-full grid grid-cols-2">
          <TabsTrigger 
            value="type" 
            className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white"
          >
            <Type className="h-4 w-4 mr-2" />
            Type Name
          </TabsTrigger>
          <TabsTrigger 
            value="draw"
            className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white"
          >
            <PenLine className="h-4 w-4 mr-2" />
            Draw Signature
          </TabsTrigger>
        </TabsList>

        <TabsContent value="type" className="mt-3">
          <div className="space-y-3">
            <Input
              type="text"
              value={typedSignature}
              onChange={handleTypedChange}
              placeholder="Type your full name as signature"
              className="rounded-xl text-lg font-signature"
              data-testid="typed-signature-input"
            />
            {typedSignature && (
              <div className="p-4 bg-white border border-[#E4E8EB] rounded-xl">
                <p className="text-xs text-text-muted mb-2">Preview:</p>
                <p className="font-signature text-2xl text-text-primary italic border-b border-dashed border-text-muted pb-2">
                  {typedSignature}
                </p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="draw" className="mt-3">
          <div className="space-y-3">
            <div className="border border-[#E4E8EB] rounded-xl overflow-hidden bg-white">
              <SignatureCanvas
                ref={sigCanvas}
                penColor="#1a1a1a"
                canvasProps={{
                  className: 'w-full h-32 touch-none',
                  style: { width: '100%', height: '128px' }
                }}
                onEnd={handleDrawEnd}
              />
            </div>
            <Button 
              type="button" 
              variant="outline" 
              size="sm" 
              onClick={handleClear}
              className="rounded-lg"
            >
              <Eraser className="h-4 w-4 mr-2" />
              Clear
            </Button>
          </div>
        </TabsContent>
      </Tabs>

      {showDate && (
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <Label className="text-xs text-text-muted">Date Signed</Label>
            <Input
              type="date"
              value={signedDate}
              onChange={handleDateChange}
              className="rounded-xl mt-1"
              data-testid="signature-date"
            />
          </div>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={!typedSignature && !signatureData}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl mt-5"
            data-testid="confirm-signature"
          >
            <Check className="h-4 w-4 mr-2" />
            Confirm
          </Button>
        </div>
      )}

      {(typedSignature || signatureData) && signedDate && (
        <div className="flex items-center gap-2 text-success text-sm">
          <Check className="h-4 w-4" />
          Signature captured
        </div>
      )}
    </div>
  );
}

// Helper component for displaying locked/completed signatures
export function SignatureDisplay({ signature, label = "Signature", className = "" }) {
  if (!signature || !signature.hasSignature) {
    return (
      <div className={`space-y-2 ${className}`}>
        <Label className="text-xs text-text-muted">{label}</Label>
        <div className="p-3 bg-[#F8FAFA] rounded-xl text-text-muted text-sm">
          Not signed
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <Label className="text-xs text-text-muted">{label}</Label>
      <div className="p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
        {signature.drawn ? (
          <img 
            src={signature.drawn} 
            alt="Signature" 
            className="max-h-16 border-b border-dashed border-text-muted"
          />
        ) : (
          <p className="font-signature text-xl text-text-primary italic border-b border-dashed border-text-muted pb-1">
            {signature.typed}
          </p>
        )}
        {signature.date && (
          <p className="text-xs text-text-muted mt-2">
            Signed: {new Date(signature.date).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}

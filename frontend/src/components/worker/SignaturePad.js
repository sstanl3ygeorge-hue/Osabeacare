import { useRef, useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import axios from 'axios';
import { Loader2, Eraser, Check, FileText, AlertCircle } from 'lucide-react';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

export default function SignaturePad({ employeeId, employeeName, onSigned, onCancel }) {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasDrawn, setHasDrawn] = useState(false);
  const [signing, setSigning] = useState(false);
  const [fullName, setFullName] = useState(employeeName || '');
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    // Initialize canvas with white background
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }, []);

  const getCoordinates = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    
    // Handle both mouse and touch events
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    
    return {
      x: (clientX - rect.left) * (canvas.width / rect.width),
      y: (clientY - rect.top) * (canvas.height / rect.height)
    };
  };

  const startDrawing = (e) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const { x, y } = getCoordinates(e);
    
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    e.preventDefault();
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const { x, y } = getCoordinates(e);
    
    ctx.lineTo(x, y);
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#1a1a2e';
    ctx.stroke();
    setHasDrawn(true);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  };

  const submitSignature = async () => {
    if (!fullName.trim()) {
      toast.error('Please enter your full legal name');
      return;
    }

    if (!hasDrawn) {
      toast.error('Please draw your signature');
      return;
    }

    if (!agreed) {
      toast.error('Please agree to the terms');
      return;
    }

    const canvas = canvasRef.current;
    const signatureData = canvas.toDataURL('image/png');
    
    setSigning(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.post(
        `${API}/worker/contract/sign`,
        { 
          signature_base64: signatureData, 
          full_name: fullName.trim() 
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Contract signed successfully!');
      if (onSigned) onSigned(response.data);
    } catch (error) {
      const detail = error.response?.data?.detail;
      const code = typeof detail === 'object' ? detail?.code : null;
      if (error.response?.status === 409 && code === 'already_has_active_contract') {
        toast.info('Contract is already signed or moved to the next stage. Refreshing dashboard.');
        if (onSigned) onSigned({ success: true, idempotent: true, detail });
        return;
      }
      const message = typeof detail === 'string'
        ? detail
        : (detail?.message || 'Failed to sign contract');
      toast.error(message);
    } finally {
      setSigning(false);
    }
  };

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="text-center pb-2">
        <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-3">
          <FileText className="h-7 w-7 text-blue-600" />
        </div>
        <CardTitle className="text-xl">Sign Your Employment Contract</CardTitle>
        <CardDescription>
          Draw your signature below to digitally sign your contract
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Signature Canvas */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Your Signature</Label>
          <div className="border-2 border-dashed border-slate-200 rounded-xl p-2 bg-slate-50">
            <canvas
              ref={canvasRef}
              width={500}
              height={150}
              className="w-full rounded-lg cursor-crosshair touch-none"
              style={{
                height: '150px',
                backgroundColor: 'white'
              }}
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawing}
              onTouchMove={draw}
              onTouchEnd={stopDrawing}
              data-testid="signature-canvas"
            />
            <div className="flex justify-between items-center mt-2">
              <p className="text-xs text-slate-400">
                {hasDrawn ? 'Signature drawn' : 'Draw your signature above'}
              </p>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={clearSignature}
                className="text-slate-500 gap-1 h-8"
              >
                <Eraser className="h-3 w-3" />
                Clear
              </Button>
            </div>
          </div>
        </div>

        {/* Full Name Input */}
        <div className="space-y-2">
          <Label htmlFor="fullName" className="text-sm font-medium">
            Full Legal Name (Printed)
          </Label>
          <Input
            id="fullName"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="h-11"
            placeholder="Enter your full name as it appears on your ID"
            data-testid="signer-name-input"
          />
        </div>

        {/* Agreement Checkbox */}
        <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl">
          <input
            type="checkbox"
            id="agree"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-1 h-4 w-4 rounded border-slate-300"
            data-testid="contract-agree-checkbox"
          />
          <label htmlFor="agree" className="text-sm text-slate-600 leading-relaxed">
            I confirm that I am <strong>{fullName || '[Your Name]'}</strong> and I agree to the 
            terms of my employment contract with Osabea Healthcare Solutions. I understand this 
            digital signature is legally binding.
          </label>
        </div>

        {/* Legal Notice */}
        <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
          <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-700">
            By signing, you are creating a legally binding digital signature. 
            Your signature will be embedded in your contract document.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <Button 
            onClick={submitSignature} 
            disabled={signing || !hasDrawn || !fullName.trim() || !agreed}
            className="flex-1 h-12 gap-2 bg-green-600 hover:bg-green-700"
            data-testid="submit-signature-btn"
          >
            {signing ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Check className="h-5 w-5" />
            )}
            {signing ? 'Signing Contract...' : 'Sign Contract'}
          </Button>
          <Button 
            type="button"
            variant="outline" 
            onClick={onCancel} 
            className="flex-1 h-12"
            disabled={signing}
          >
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}


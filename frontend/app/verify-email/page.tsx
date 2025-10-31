'use client';

import { apiRequest } from '@/lib/api-secure';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Leaf } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided');
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await apiRequest(`http://localhost:8000/auth/verify-email?token=${token}`);
        
        if (response.ok) {
          setStatus('success');
          setMessage('Email verified successfully! You can now sign in.');
        } else {
          setStatus('error');
          setMessage('Invalid or expired verification token.');
        }
      } catch (error) {
        setStatus('error');
        setMessage('Failed to verify email. Please try again.');
      }
    };

    verifyEmail();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 via-te Brave-50 to-cyan-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate PAS900 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="shadow-lg border-2">
          <CardHeader className="text-center">
            <Link href="/" className="flex items-center justify-center gap-3 mb-4">
              <Leaf className="h-8 w-8 text-emerald-600 dark:text-emerald-500" />
              <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                  VeriEarth
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Email Verification
                </p>
              </div>
            </Link>
          </CardHeader>
          <CardContent className="text-center space-y-6">
            {status === 'loading' && (
              <>
                <Loader2 className="h-16 w-16 mx-auto text-emerald-600 animate-spin" />
                <CardTitle>Verifying your email...</CardTitle>
                <CardDescription>Please wait while we verify your email address.</CardDescription>
              </>
            )}
            
            {status === 'success' && (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring" }}
                >
                  <CheckCircle className="h-16 w-16 mx-auto text-emerald-600" />
                </motion.div>
                <CardTitle className="text-emerald-600">Verification Successful!</CardTitle>
                <CardDescription>{message}</CardDescription>
                <Link href="/signin">
                  <Button className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white">
                    Sign In Now
                  </Button>
                </Link>
              </>
            )}
            
            {status === 'error' && (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring" }}
                >
                  <XCircle className="h-16 w-16 mx-auto text-red-600" />
                </motion.div>
                <CardTitle className="text-red-600">Verification Failed</CardTitle>
                <CardDescription>{message}</CardDescription>
                <div className="space-y-2">
                  <Link href="/signin">
                    <Button variant="outline" className="w-full">
                      Go to Sign In
                    </Button>
                  </Link>
                  <Link href="/signup">
                    <Button variant="ghost" className="w-full">
                      Sign Up Again
                    </Button>
                  </Link>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}


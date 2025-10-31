'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { TextGenerateEffect } from '@/components/ui/text-generate-effect';
import { SparklesCore } from '@/components/ui/sparkles';
import { 
  Leaf, 
  ArrowRight, 
  TrendingDown,
  Target,
  Zap,
  ShieldCheck,
  BarChart3,
  MapPin,
  CheckCircle2,
  Play,
  Lightbulb
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement actual auth
    router.push('/dashboard');
  };

  const benefits = [
    {
      icon: Target,
      title: 'Identify True Emission Sources',
      description: 'Discover both frequent, high-impact patterns and rare but critical emission events that traditional analysis misses',
    },
    {
      icon: Play,
      title: 'Test Before You Invest',
      description: 'Simulate decarbonization strategies—mode shifts, route changes, supplier switches—before implementation',
    },
    {
      icon: MapPin,
      title: 'Real-Time Environmental Data',
      description: 'Integrate live satellite data and ground sensors for geospatially contextualized emissions tracking',
    },
    {
      icon: BarChart3,
      title: 'Focus Resources Where It Matters',
      description: 'Prioritize interventions on the 20% of routes that generate 80% of your supply chain emissions',
    },
  ];

  const features = [
    'Supply Network Knowledge Graph',
    'Earth Observation Data Integration',
    'Sequential Pattern Mining',
    'Prescriptive What-If Simulation',
    'Multi-Objective Optimization',
    'Enterprise-Ready SaaS Dashboard',
  ];

  const textVariants = [
    'Track Carbon Hotspots',
    'Optimize Supply Routes',
    'Monitor Air Quality',
    'Predict Emissions Patterns',
    'Simulate Decarbonization',
  ];

  const [currentTextIndex, setCurrentTextIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTextIndex((prev) => (prev + 1) % textVariants.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const socialProof = [
    'SEBI BRSR Compliant',
    'ISO 14083:2023 Aligned',
    'GHG Protocol Scope 3 Ready',
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Header with Branding */}
      <header className="relative z-50 border-b border-slate-200 dark:border-emerald-900/20 bg-white/95 dark:bg-black/95 backdrop-blur-md sticky top-0">
        <div className="container px-4 mx-auto py-4">
          <div className="flex items-center justify-between">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3"
            >
              <Leaf className="h-8 w-8 text-emerald-600 dark:text-emerald-500" />
              <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                  VeriEarth
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Supply Chain Intelligence
                </p>
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-4"
            >
              <Button variant="ghost" onClick={() => router.push('/signin')}>
                Sign In
              </Button>
              <Button 
                className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white"
                onClick={() => router.push('/signup')}
              >
                Get Started
              </Button>
            </motion.div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-32 bg-white dark:bg-black">
        {/* Animated background */}
        <div className="absolute inset-0 overflow-hidden">
          <motion.div
            className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 dark:bg-emerald-500 dark:opacity-15 dark:mix-blend-lighten"
            animate={{
              scale: [1, 1.2, 1],
              x: [0, 50, 0],
            }}
            transition={{ duration: 15, repeat: Infinity }}
          />
          <motion.div
            className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 dark:bg-emerald-400 dark:opacity-15 dark:mix-blend-lighten"
            animate={{
              scale: [1, 1.3, 1],
              x: [0, -50, 0],
            }}
            transition={{ duration: 18, repeat: Infinity }}
          />
        </div>

        <div className="container relative z-10 px-4 mx-auto">
          <div className="max-w-5xl mx-auto text-center space-y-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-100 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30">
                <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
                  Enterprise Supply Chain Intelligence
                </span>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="space-y-4"
            >
              <div className="relative w-full flex flex-col items-center justify-center">
                <h1 className="text-6xl md:text-7xl font-bold text-slate-800 dark:text-slate-100 relative z-20 mb-4">
                  <TextGenerateEffect 
                    key={currentTextIndex}
                    words={textVariants[currentTextIndex]} 
                    className="bg-gradient-to-r from-emerald-600 via-emerald-500 to-green-600 dark:from-emerald-400 dark:via-emerald-300 dark:to-green-400 bg-clip-text text-transparent text-6xl md:text-7xl font-bold"
                  />
                </h1>
                <div className="w-[40rem] h-40 relative -mt-32 -z-10">
                  <SparklesCore
                    id="tsparticlesfullpage"
                    background="transparent"
                    minSize={0.6}
                    maxSize={1.4}
                    particleDensity={100}
                    className="w-full h-full"
                    particleColor="#FFFFFF"
                  />
                </div>
              </div>
              <p className="text-xl text-slate-600 dark:text-slate-300 max-w-3xl mx-auto">
                The first integrated platform combining sequential pattern mining with satellite data
                to identify and eliminate the hidden emission patterns costing your business
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
            >
              <Button
                size="lg"
                className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white text-lg px-8 py-6"
                onClick={() => router.push('/signup')}
              >
                View Demo
                <Play className="ml-2 h-5 w-5" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="border-2 text-lg px-8 py-6"
                onClick={() => router.push('/signin')}
              >
                Explore Platform
                <Play className="ml-2 h-5 w-5" />
              </Button>
            </motion.div>

          </div>
        </div>
      </section>

      {/* Problem Statement */}
      <section className="py-20 bg-slate-50 dark:bg-slate-950">
        <div className="container px-4 mx-auto">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <h2 className="text-4xl font-bold text-slate-900 dark:text-white">
              Traditional Analysis Misses the Real Problems
            </h2>
            <p className="text-lg text-slate-600 dark:text-slate-300">
              Most carbon accounting tools flag single, dramatic events—but miss the 
              <strong className="text-emerald-600 dark:text-emerald-400"> frequent, medium-impact routes</strong> that silently accumulate 30x more emissions annually.
            </p>
          </div>
        </div>
      </section>

      {/* Benefits Grid */}
      <section className="py-20 bg-white dark:bg-black">
        <div className="container px-4 mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
              Why Leading Companies Should Choose VeriEarth
            </h2>
            <p className="text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
              The only platform that combines pattern analysis, real-time environmental data, and prescriptive simulation
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {benefits.map((benefit, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ scale: 1.02, y: -4 }}
                className="bg-slate-50 dark:bg-slate-900 p-8 rounded-2xl shadow-lg border border-slate-200 dark:border-emerald-900/30 hover:shadow-xl transition-all hover:border-emerald-500/50"
              >
                <benefit.icon className="h-10 w-10 text-emerald-500 dark:text-emerald-400 mb-4" />
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                  {benefit.title}
                </h3>
                <p className="text-slate-600 dark:text-slate-300">
                  {benefit.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-slate-50 dark:bg-slate-950">
        <div className="container px-4 mx-auto">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
                Enterprise-Grade Technology Stack
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950 dark:to-teal-950 p-6 rounded-xl border border-emerald-200 dark:border-emerald-800"
                >
                  <div className="flex items-start gap-3">
                    <Zap className="h-5 w-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span className="font-medium text-slate-700 dark:text-slate-300">
                      {feature}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>


      {/* Footer */}
      <footer className="py-8 border-t border-emerald-200 dark:border-emerald-800 bg-white/50 dark:bg-slate-900/50">
        <div className="container px-4 mx-auto text-center text-sm text-slate-600 dark:text-slate-400">
          <p>© 2025 VeriEarth. Empower your supply chain decarbonization journey.</p>
        </div>
      </footer>
    </div>
  );
}

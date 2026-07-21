import React from 'react';
import { motion } from 'framer-motion';

export const OrbBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10 bg-[#07090e]">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-grid-pattern opacity-30" />

      {/* Orb 1: Purple */}
      <motion.div
        animate={{
          x: [0, 80, -40, 0],
          y: [0, -60, 40, 0],
          scale: [1, 1.2, 0.9, 1],
        }}
        transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-purple-600/20 blur-[120px]"
      />

      {/* Orb 2: Cyan */}
      <motion.div
        animate={{
          x: [0, -70, 50, 0],
          y: [0, 80, -50, 0],
          scale: [1, 1.15, 0.95, 1],
        }}
        transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-1/3 -right-32 w-[30rem] h-[30rem] rounded-full bg-cyan-500/15 blur-[140px]"
      />

      {/* Orb 3: Pink */}
      <motion.div
        animate={{
          x: [0, 60, -60, 0],
          y: [0, 50, -70, 0],
          scale: [1, 1.3, 0.85, 1],
        }}
        transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute -bottom-32 left-1/4 w-[28rem] h-[28rem] rounded-full bg-pink-500/15 blur-[130px]"
      />
    </div>
  );
};

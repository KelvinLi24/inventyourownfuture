#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const homepage = path.join(root, 'index.html');
const heroSectionId = '68ffdc2451780627bfb438cc';
const expectedSlides = 5;

const html = fs.readFileSync(homepage, 'utf8');

const carouselStart = html.indexOf('data-controller="UserItemsListCarousel"', html.indexOf(`data-section-id="${heroSectionId}"`) - 5000);
const listStart = html.indexOf('<ul class="user-items-list-carousel__slides', carouselStart);
const listEnd = html.indexOf('</ul>', listStart);

if (carouselStart < 0 || listStart < 0 || listEnd < 0) {
  throw new Error(`Could not find homepage hero carousel ${heroSectionId}`);
}

const listHtml = html.slice(listStart, listEnd + 5);
const slides = [...listHtml.matchAll(/<li\b[\s\S]*?user-items-list-carousel__slide[\s\S]*?<\/li>/g)].map((match) => match[0]);

if (slides.length !== expectedSlides) {
  throw new Error(`Expected ${expectedSlides} hero slides, found ${slides.length}`);
}

const seen = new Set();
const failures = [];

slides.forEach((slide, index) => {
  const imgTag = slide.match(/<img\b[^>]*>/)?.[0] || '';
  const dataSrc = imgTag.match(/\bdata-src="([^"]+)"/)?.[1] || '';
  const dataImage = imgTag.match(/\bdata-image="([^"]+)"/)?.[1] || '';

  if (!dataSrc) failures.push(`Slide ${index + 1} is missing data-src`);
  if (!dataImage) failures.push(`Slide ${index + 1} is missing data-image`);
  if (dataSrc && dataImage && dataSrc !== dataImage) failures.push(`Slide ${index + 1} data-src and data-image differ`);
  if (dataSrc.includes('invent.png')) failures.push(`Slide ${index + 1} points to logo fallback invent.png`);
  if (dataSrc && seen.has(dataSrc)) failures.push(`Slide ${index + 1} duplicates ${dataSrc}`);
  if (dataSrc) seen.add(dataSrc);

  const assetPath = dataSrc ? path.join(root, dataSrc) : '';
  if (dataSrc && !fs.existsSync(assetPath)) failures.push(`Slide ${index + 1} asset does not exist: ${dataSrc}`);
});

if (failures.length) {
  throw new Error(`Hero carousel check failed:\n${failures.join('\n')}`);
}

console.log(`Hero carousel OK: ${slides.length}/${expectedSlides} slides with local image assets.`);

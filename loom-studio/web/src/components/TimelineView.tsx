
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { CloudEvent } from '../types';

interface TimelineViewProps {
  events: CloudEvent[];
}

const TimelineView: React.FC<TimelineViewProps> = ({ events }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !wrapperRef.current || events.length === 0) return;

    const wrapper = wrapperRef.current;
    const width = wrapper.clientWidth;
    const height = wrapper.clientHeight;
    const margin = { top: 20, right: 20, bottom: 30, left: 100 };

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Parse times
    const parsedEvents = events.map(e => ({
        ...e,
        parsedTime: new Date(Number(e.time) * 1000) 
        // Note: SDK sends time.time(), usually float seconds
        // But CloudEvent spec says time is string ISO8601 usually.
        // Let's check our interceptor: stored as extensions["studio_timestamp"] = time.time()
        // And standard 'time' field might be ISO string
        // Let's use studio_timestamp if available, else time field
    })).map(e => {
        let t = e.extensions?.studio_timestamp;
        if (!t) {
             t = new Date(e.time).getTime() / 1000;
        }
        return { ...e, timeValue: t };
    });

    if (parsedEvents.length === 0) return;

    const minTime = d3.min(parsedEvents, d => d.timeValue) || 0;
    const maxTime = d3.max(parsedEvents, d => d.timeValue) || 0;

    // Scales
    const xScale = d3.scaleLinear()
      .domain([minTime, maxTime])
      .range([margin.left, width - margin.right]);

    // Group by source or type for Y axis? 
    // Let's use source (Node ID) for Y axis lanes
    const sources = Array.from(new Set(parsedEvents.map(e => e.source))).sort();
    
    const yScale = d3.scaleBand()
      .domain(sources)
      .range([margin.top, height - margin.bottom])
      .padding(0.1);

    // X Axis
    const xAxis = d3.axisBottom(xScale)
        .tickFormat(d => {
            const date = new Date(Number(d) * 1000);
            return date.toLocaleTimeString();
        });

    svg.append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(xAxis);

    // Y Axis
    svg.append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(yScale));

    // Events
    svg.selectAll('circle')
      .data(parsedEvents)
      .enter()
      .append('circle')
      .attr('cx', d => xScale(d.timeValue))
      .attr('cy', d => (yScale(d.source) || 0) + yScale.bandwidth() / 2)
      .attr('r', 5)
      .attr('fill', d => {
        if (d.type.includes('error')) return '#ef5350';
        if (d.type.includes('agent')) return '#66bb6a';
        if (d.type.includes('tool')) return '#42a5f5';
        return '#bdbdbd';
      })
      .attr('opacity', 0.8)
      .on('mouseover', function() {
          d3.select(this).attr('r', 8).attr('fill', '#fff');
          // Simple tooltip logic could go here
      })
      .on('mouseout', function(_event, _d) {
          d3.select(this).attr('r', 5).attr('fill', (d: any) => {
            if (d.type.includes('error')) return '#ef5350';
            if (d.type.includes('agent')) return '#66bb6a';
            if (d.type.includes('tool')) return '#42a5f5';
            return '#bdbdbd';
          });
      })
      .append('title') // Browser tooltip
      .text(d => `${d.type}\n${JSON.stringify(d.data, null, 2)}`);

  }, [events]);

  return (
    <div ref={wrapperRef} style={{ width: '100%', height: '100%', backgroundColor: '#1e1e1e' }}>
       <svg ref={svgRef} width="100%" height="100%" />
    </div>
  );
};

export default TimelineView;

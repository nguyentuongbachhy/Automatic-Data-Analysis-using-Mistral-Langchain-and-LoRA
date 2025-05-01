import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ResponsiveContainer } from 'recharts';
import { formatNumber } from '../../utils/chart';

// Màu sắc cho biểu đồ
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

interface NetworkNode {
    id: string;
    name?: string;
    group?: string;
    value?: number;
    x?: number;
    y?: number;
    color?: string;
    fixed?: boolean;
}

interface NetworkLink {
    source: string;
    target: string;
    value?: number;
    label?: string;
    color?: string;
}

interface NetworkChartRendererProps {
    data: { nodes?: any[]; links?: any[] } | any[];
    title?: string;
    description?: string;
    config?: {
        nodeRadius?: number;
        maxNodeRadius?: number;
        linkDistance?: number;
        linkStrength?: number;
        charge?: number;
        gravity?: number;
        directed?: boolean;
        colorByGroup?: boolean;
        showLabels?: boolean;
        labelSize?: number;
        simulationIterations?: number;
        highlightNeighbors?: boolean;
        dragEnabled?: boolean;
        zoomEnabled?: boolean;
        legendEnabled?: boolean;
        nodeClick?: (nodeId: string) => void;
    };
}

export default function NetworkChartRenderer({
    data,
    title,
    description,
    config = {}
}: NetworkChartRendererProps) {
    // Reference cho container SVG
    const svgRef = useRef<SVGSVGElement | null>(null);
    const tooltipRef = useRef<HTMLDivElement | null>(null);

    // State cho network simulation
    const [dimensions, setDimensions] = useState({ width: 300, height: 200 });
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const [selectedNode, setSelectedNode] = useState<string | null>(null);
    const [dragging, setDragging] = useState<string | null>(null);
    const translate = { x: 0, y: 0, k: 1 };

    // Cấu hình mặc định
    const {
        nodeRadius = 5,
        maxNodeRadius = 20,
        linkDistance = 100,
        linkStrength = 0.7,
        charge = -100,
        gravity = 0.1,
        directed = false,
        colorByGroup = true,
        showLabels = true,
        labelSize = 10,
        simulationIterations = 300,
        highlightNeighbors = true,
        dragEnabled = true,
        legendEnabled = true,
        nodeClick = undefined
    } = config;

    // Parse network data
    const { nodes, links, groups } = useMemo(() => {
        if (!data || (Array.isArray(data) && data.length === 0)) return { nodes: [], links: [], groups: [] };

        // If data has nodes and links properties
        if (!Array.isArray(data) && Array.isArray(data.nodes) && Array.isArray(data.links)) {
            const parsedNodes = (data.nodes as any[]).map(node => ({
                id: String(node.id),
                name: node.name || node.id,
                group: node.group || 'default',
                value: Number(node.value || node.size || 1),
                x: node.x,
                y: node.y,
                color: node.color,
                fixed: !!node.fixed
            }));

            const parsedLinks = (data.links as any[]).map(link => ({
                source: String(link.source),
                target: String(link.target),
                value: Number(link.value || link.weight || 1),
                label: link.label,
                color: link.color
            }));

            const extractedGroups = [...new Set(parsedNodes.map(node => node.group))];

            return {
                nodes: parsedNodes,
                links: parsedLinks,
                groups: extractedGroups
            };
        }

        // Alternative format: array of link objects
        if (Array.isArray(data) && data[0] && ('source' in data[0] || 'from' in data[0]) && ('target' in data[0] || 'to' in data[0])) {
            // Extract unique nodes from links
            const nodeMap: Record<string, NetworkNode> = {};
            const parsedLinks: NetworkLink[] = [];

            data.forEach(link => {
                const sourceId = String(link.source || link.from);
                const targetId = String(link.target || link.to);
                const weight = Number(link.value || link.weight || 1);

                // Add source node if not exists
                if (!nodeMap[sourceId]) {
                    nodeMap[sourceId] = {
                        id: sourceId,
                        name: link.sourceName || sourceId,
                        group: link.sourceGroup || 'default',
                        value: 0
                    };
                }

                // Add target node if not exists
                if (!nodeMap[targetId]) {
                    nodeMap[targetId] = {
                        id: targetId,
                        name: link.targetName || targetId,
                        group: link.targetGroup || 'default',
                        value: 0
                    };
                }

                // Count connections for node size
                nodeMap[sourceId].value = (nodeMap[sourceId].value || 0) + weight;
                nodeMap[targetId].value = (nodeMap[targetId].value || 0) + weight;

                // Add link
                parsedLinks.push({
                    source: sourceId,
                    target: targetId,
                    value: weight,
                    label: link.label,
                    color: link.color
                });
            });

            const parsedNodes = Object.values(nodeMap);
            const extractedGroups = [...new Set(parsedNodes.map(node => node.group))];

            return {
                nodes: parsedNodes,
                links: parsedLinks,
                groups: extractedGroups
            };
        }

        return { nodes: [], links: [], groups: [] };
    }, [data]);

    // Xác định neighbors của mỗi node
    const neighborMap = useMemo(() => {
        const map: Record<string, Set<string>> = {};

        // Initialize empty sets for all nodes
        nodes.forEach(node => {
            map[node.id] = new Set<string>();
        });

        // Add neighbors based on links
        links.forEach(link => {
            if (map[link.source]) {
                map[link.source].add(link.target);
            }
            if (map[link.target]) {
                map[link.target].add(link.source);
            }
        });

        return map;
    }, [nodes, links]);

    // Color generation for nodes based on group
    const getNodeColor = useCallback((node: NetworkNode) => {
        if (node.color) return node.color;

        if (colorByGroup && node.group) {
            const groupIndex = groups.indexOf(node.group);
            return groupIndex >= 0 ? COLORS[groupIndex % COLORS.length] : COLORS[0];
        }

        return COLORS[0];
    }, [colorByGroup, groups]);

    // Calculate node and link opacities based on selection/hover
    const getNodeOpacity = useCallback((nodeId: string) => {
        if (!hoveredNode && !selectedNode) return 1;

        if (nodeId === hoveredNode || nodeId === selectedNode) return 1;

        if (highlightNeighbors && (hoveredNode || selectedNode)) {
            const activeNode = hoveredNode || selectedNode;
            if (activeNode && neighborMap[activeNode].has(nodeId)) return 0.8;
        }

        return 0.3;
    }, [hoveredNode, selectedNode, neighborMap, highlightNeighbors]);

    const getLinkOpacity = useCallback((source: string, target: string) => {
        if (!hoveredNode && !selectedNode) return 0.6;

        if (hoveredNode || selectedNode) {
            const activeNode = hoveredNode || selectedNode;
            if (activeNode === source || activeNode === target) return 0.8;
        }

        return 0.1;
    }, [hoveredNode, selectedNode]);

    // Calculate node radius based on value
    const getNodeRadius = useCallback((node: NetworkNode) => {
        if (!node.value || node.value <= 0) return nodeRadius;

        // Find min/max values for scaling
        const values = nodes.map(n => n.value || 0);
        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);

        if (minValue === maxValue) return nodeRadius;

        // Scale radius between nodeRadius and maxNodeRadius
        const normalizedValue = (node.value - minValue) / (maxValue - minValue);
        return nodeRadius + normalizedValue * (maxNodeRadius - nodeRadius);
    }, [nodes, nodeRadius, maxNodeRadius]);

    // Force-directed layout calculation (simple version)
    useEffect(() => {
        if (!svgRef.current || nodes.length === 0) return;

        const width = dimensions.width;
        const height = dimensions.height;

        // Initialize positions if not set
        const simulationNodes = nodes.map(node => ({
            ...node,
            x: node.x || Math.random() * width,
            y: node.y || Math.random() * height,
            radius: getNodeRadius(node)
        }));

        // Map link references
        const simulationLinks = links.map(link => ({
            ...link,
            sourceNode: simulationNodes.find(n => n.id === link.source),
            targetNode: simulationNodes.find(n => n.id === link.target)
        }));

        // Very simple force simulation
        // In a real implementation, you would use d3-force or a similar library
        for (let i = 0; i < simulationIterations; i++) {
            // Apply link forces
            simulationLinks.forEach(link => {
                if (!link.sourceNode || !link.targetNode) return;

                const dx = link.targetNode.x! - link.sourceNode.x!;
                const dy = link.targetNode.y! - link.sourceNode.y!;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance === 0) return;

                // Attractive force
                const force = (distance - linkDistance) * linkStrength;
                const fx = (dx / distance) * force;
                const fy = (dy / distance) * force;

                if (!link.sourceNode.fixed) {
                    link.sourceNode.x! += fx;
                    link.sourceNode.y! += fy;
                }

                if (!link.targetNode.fixed) {
                    link.targetNode.x! -= fx;
                    link.targetNode.y! -= fy;
                }
            });

            // Apply repulsive forces between nodes
            for (let j = 0; j < simulationNodes.length; j++) {
                for (let k = j + 1; k < simulationNodes.length; k++) {
                    const nodeA = simulationNodes[j];
                    const nodeB = simulationNodes[k];

                    if (nodeA.fixed && nodeB.fixed) continue;

                    const dx = nodeB.x! - nodeA.x!;
                    const dy = nodeB.y! - nodeA.y!;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance === 0) continue;

                    // Repulsive force
                    const force = charge / (distance * distance);
                    const fx = (dx / distance) * force;
                    const fy = (dy / distance) * force;

                    if (!nodeA.fixed) {
                        nodeA.x! -= fx;
                        nodeA.y! -= fy;
                    }

                    if (!nodeB.fixed) {
                        nodeB.x! += fx;
                        nodeB.y! += fy;
                    }
                }
            }

            // Center gravity
            simulationNodes.forEach(node => {
                if (node.fixed) return;

                node.x! += (width / 2 - node.x!) * gravity;
                node.y! += (height / 2 - node.y!) * gravity;

                // Keep within bounds
                node.x = Math.max(node.radius!, Math.min(width - node.radius!, node.x!));
                node.y = Math.max(node.radius!, Math.min(height - node.radius!, node.y!));
            });
        }

        // Update original nodes with new positions
        simulationNodes.forEach(simNode => {
            const originalNode = nodes.find(n => n.id === simNode.id);
            if (originalNode) {
                originalNode.x = simNode.x;
                originalNode.y = simNode.y;
            }
        });
    }, [
        nodes, links, dimensions,
        linkDistance, linkStrength, charge, gravity,
        simulationIterations, getNodeRadius
    ]);

    // Handle container resize
    useEffect(() => {
        if (!svgRef.current) return;

        const updateDimensions = () => {
            const container = svgRef.current?.parentElement;
            if (container) {
                setDimensions({
                    width: container.clientWidth,
                    height: container.clientHeight
                });
            }
        };

        // Initial update
        updateDimensions();

        // Update on resize
        window.addEventListener('resize', updateDimensions);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    // Handle node drag
    const handleNodeMouseDown = useCallback((nodeId: string, event: React.MouseEvent) => {
        if (!dragEnabled) return;

        event.stopPropagation();
        setDragging(nodeId);

        // Find and set the node as fixed
        const node = nodes.find(n => n.id === nodeId);
        if (node) {
            node.fixed = true;
        }
    }, [dragEnabled, nodes]);

    const handleMouseMove = useCallback((event: React.MouseEvent) => {
        if (!dragging || !svgRef.current) return;

        // Calculate position in SVG coordinates
        const svg = svgRef.current;
        const pt = svg.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());

        // Update dragged node position
        const draggedNode = nodes.find(n => n.id === dragging);
        if (draggedNode) {
            draggedNode.x = (svgP.x - translate.x) / translate.k;
            draggedNode.y = (svgP.y - translate.y) / translate.k;
        }
    }, [dragging, nodes, translate]);

    const handleMouseUp = useCallback(() => {
        if (dragging) {
            const draggedNode = nodes.find(n => n.id === dragging);
            if (draggedNode) {
                draggedNode.fixed = false;
            }
            setDragging(null);
        }
    }, [dragging, nodes]);

    // Handle node hover
    const handleNodeHover = useCallback((nodeId: string | null, event: React.MouseEvent | null) => {
        setHoveredNode(nodeId);

        // Update tooltip position
        if (nodeId && event && tooltipRef.current) {
            tooltipRef.current.style.left = `${event.clientX + 10}px`;
            tooltipRef.current.style.top = `${event.clientY + 10}px`;
            tooltipRef.current.style.display = 'block';
        } else if (tooltipRef.current) {
            tooltipRef.current.style.display = 'none';
        }
    }, []);

    // Handle node click
    const handleNodeClick = useCallback((nodeId: string, event: React.MouseEvent) => {
        event.stopPropagation();

        setSelectedNode(prev => prev === nodeId ? null : nodeId);

        if (nodeClick) {
            nodeClick(nodeId);
        }
    }, [nodeClick]);

    // Handle background click
    const handleBackgroundClick = useCallback(() => {
        setSelectedNode(null);
    }, []);

    // Render arrow markers for directed graphs
    const renderArrowMarkers = useCallback(() => {
        if (!directed) return null;

        return (
            <defs>
                <marker
                    id="arrowhead"
                    viewBox="0 -5 10 10"
                    refX="8"
                    refY="0"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto"
                >
                    <path d="M0,-5L10,0L0,5" fill="#999" />
                </marker>
            </defs>
        );
    }, [directed]);

    // Render links
    const renderLinks = useCallback(() => {
        return links.map((link, index) => {
            const sourceNode = nodes.find(n => n.id === link.source);
            const targetNode = nodes.find(n => n.id === link.target);

            if (!sourceNode || !targetNode ||
                sourceNode.x === undefined || sourceNode.y === undefined ||
                targetNode.x === undefined || targetNode.y === undefined) {
                return null;
            }

            // Calculate path adjustments for arrow direction
            const sourceRadius = getNodeRadius(sourceNode);
            const targetRadius = getNodeRadius(targetNode);

            const dx = targetNode.x - sourceNode.x;
            const dy = targetNode.y - sourceNode.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance === 0) return null;

            // Calculate end points that stop at node boundaries
            const sourceX = sourceNode.x + (dx / distance) * sourceRadius;
            const sourceY = sourceNode.y + (dy / distance) * sourceRadius;
            const targetX = targetNode.x - (dx / distance) * targetRadius;
            const targetY = targetNode.y - (dy / distance) * targetRadius;

            return (
                <line
                    key={`link-${index}`}
                    x1={sourceX}
                    y1={sourceY}
                    x2={targetX}
                    y2={targetY}
                    stroke={link.color || '#999'}
                    strokeWidth={Math.max(1, Math.min(3, link.value || 1))}
                    strokeOpacity={getLinkOpacity(link.source, link.target)}
                    markerEnd={directed ? "url(#arrowhead)" : undefined}
                />
            );
        });
    }, [links, nodes, getNodeRadius, getLinkOpacity, directed]);

    // Render nodes
    const renderNodes = useCallback(() => {
        return nodes.map((node, index) => {
            if (node.x === undefined || node.y === undefined) return null;

            const radius = getNodeRadius(node);
            const color = getNodeColor(node);
            const opacity = getNodeOpacity(node.id);

            return (
                <g
                    key={`node-${index}`}
                    transform={`translate(${node.x}, ${node.y})`}
                    onMouseEnter={(e) => handleNodeHover(node.id, e)}
                    onMouseLeave={() => handleNodeHover(null, null)}
                    onClick={(e) => handleNodeClick(node.id, e)}
                    onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
                    style={{ cursor: dragEnabled ? 'grab' : 'pointer' }}
                >
                    <circle
                        r={radius}
                        fill={color}
                        stroke="#fff"
                        strokeWidth="1.5"
                        opacity={opacity}
                    />

                    {showLabels && (
                        <text
                            x="0"
                            y={radius + 4}
                            textAnchor="middle"
                            fontSize={labelSize}
                            fill="#333"
                            opacity={opacity}
                        >
                            {node.name || node.id}
                        </text>
                    )}
                </g>
            );
        });
    }, [
        nodes, getNodeRadius, getNodeColor, getNodeOpacity,
        showLabels, labelSize, dragEnabled,
        handleNodeHover, handleNodeClick, handleNodeMouseDown
    ]);

    // Render legend
    const renderLegend = useCallback(() => {
        if (!legendEnabled || !colorByGroup || groups.length === 0) return null;

        return (
            <div className="flex flex-wrap justify-center gap-2 mt-2 text-sm">
                {groups.map((group, index) => (
                    <div key={index} className="flex items-center">
                        <div
                            className="w-3 h-3 rounded-full mr-1"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span>{group}</span>
                    </div>
                ))}
            </div>
        );
    }, [legendEnabled, colorByGroup, groups]);

    // Render tooltip
    const renderTooltip = useCallback(() => {
        if (!hoveredNode) return null;

        const node = nodes.find(n => n.id === hoveredNode);
        if (!node) return null;

        return (
            <div
                ref={tooltipRef}
                className="absolute bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white z-10"
                style={{ display: 'none', pointerEvents: 'none' }}
            >
                <div className="font-medium">{node.name || node.id}</div>
                {node.group && <div>Group: {node.group}</div>}
                {node.value !== undefined && <div>Value: {formatNumber(node.value)}</div>}
                <div>Connections: {neighborMap[node.id]?.size || 0}</div>
            </div>
        );
    }, [hoveredNode, nodes, neighborMap]);

    // Check if there's data to display
    if (nodes.length === 0 || links.length === 0) {
        return (
            <div className="h-full w-full flex items-center justify-center">
                <div className="text-gray-500">Không có dữ liệu cho biểu đồ mạng lưới</div>
            </div>
        );
    }

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
                <div className="text-xs text-gray-500 mt-1">
                    {nodes.length} nodes, {links.length} connections
                </div>
            </div>

            <div className="h-full w-full relative">
                <ResponsiveContainer width="99%" height={title ? "92%" : "99%"}>
                    <div className="h-full w-full">
                        <svg
                            ref={svgRef}
                            width="100%"
                            height="100%"
                            onClick={handleBackgroundClick}
                            onMouseMove={handleMouseMove}
                            onMouseUp={handleMouseUp}
                            onMouseLeave={handleMouseUp}
                        >
                            {renderArrowMarkers()}
                            <g transform={`translate(${translate.x},${translate.y}) scale(${translate.k})`}>
                                {renderLinks()}
                                {renderNodes()}
                            </g>
                        </svg>
                    </div>
                </ResponsiveContainer>

                {renderLegend()}
                {renderTooltip()}
            </div>
        </div>
    );
}
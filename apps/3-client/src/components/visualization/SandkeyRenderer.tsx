import { useMemo } from 'react';
import { ResponsiveContainer } from 'recharts';

// COLORS array for consistent styling
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

interface SankeyLink {
    source: string | number;
    target: string | number;
    value: number;
    color?: string;
}

interface SankeyNode {
    id: string | number;
    name?: string;
    color?: string;
}

interface SankeyRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        nodeWidth?: number;
        nodePadding?: number;
        margin?: { top: number; right: number; bottom: number; left: number };
        height?: number;
        width?: number;
        iterations?: number;
    };
}

export default function SankeyRenderer({
    data,
    title,
    description
}: SankeyRendererProps) {
    // Process data into format required for Sankey diagram
    const { links, nodes } = useMemo(() => {
        if (!data || data.length === 0) return { links: [], nodes: [] };

        // Handle different data formats
        let sankeyLinks: SankeyLink[] = [];
        const nodeMap = new Map<string | number, SankeyNode>();

        // Try to extract links
        if (Array.isArray(data)) {
            if (data[0] && ('source' in data[0] || 'from' in data[0]) && ('target' in data[0] || 'to' in data[0])) {
                // Data is already in link format
                sankeyLinks = data.map(item => {
                    const source = String(item.source || item.from);
                    const target = String(item.target || item.to);
                    const value = Number(item.value || item.weight || item.amount || 1);

                    // Add nodes to map if they don't exist
                    if (!nodeMap.has(source)) {
                        nodeMap.set(source, { id: source, name: source });
                    }

                    if (!nodeMap.has(target)) {
                        nodeMap.set(target, { id: target, name: target });
                    }

                    return {
                        source,
                        target,
                        value
                    };
                });
            }
        }

        // Extract array of nodes from the map
        const sankeyNodes = Array.from(nodeMap.values());

        // Assign colors to nodes
        sankeyNodes.forEach((node, index) => {
            node.color = COLORS[index % COLORS.length];
        });

        // Assign colors to links based on source node
        sankeyLinks.forEach(link => {
            const sourceNode = sankeyNodes.find(node => node.id === link.source);
            if (sourceNode) {
                link.color = sourceNode.color;
            }
        });

        return {
            links: sankeyLinks,
            nodes: sankeyNodes
        };
    }, [data]);

    // Simplified Sankey diagram rendering
    // In a real implementation, you would use a proper Sankey layout algorithm
    const renderSankey = useMemo(() => {
        if (links.length === 0 || nodes.length === 0) {
            return (
                <div className="flex items-center justify-center h-full">
                    <div className="text-gray-500">No data to display or data is not in Sankey format</div>
                </div>
            );
        }

        // Get unique sources and targets for layout
        const sources = [...new Set(links.map(link => link.source))];
        const targets = [...new Set(links.map(link => link.target))];

        // Find nodes that are only sources (left side)
        const sourceOnly = sources.filter(source => !targets.includes(source));

        // Find nodes that are only targets (right side)
        const targetOnly = targets.filter(target => !sources.includes(target));

        // Find nodes that are both sources and targets (middle)
        const middle = sources.filter(source => targets.includes(source));

        // Calculate max value for scaling
        const maxValue = Math.max(...links.map(link => link.value));

        // Calculate node positions (simplified layout)
        const nodePositions = new Map<string | number, { x: number, y: number, height: number }>();

        // Position left nodes
        let yPos = 10;
        sourceOnly.forEach(id => {
            const outgoingLinks = links.filter(link => link.source === id);
            const totalValue = outgoingLinks.reduce((sum, link) => sum + link.value, 0);
            const height = Math.max(20, (totalValue / maxValue) * 100);

            nodePositions.set(id, { x: 50, y: yPos, height });
            yPos += height + 20; // Add spacing between nodes
        });

        // Position middle nodes
        yPos = 10;
        middle.forEach(id => {
            const outgoingLinks = links.filter(link => link.source === id);
            const totalValue = outgoingLinks.reduce((sum, link) => sum + link.value, 0);
            const height = Math.max(20, (totalValue / maxValue) * 100);

            nodePositions.set(id, { x: 300, y: yPos, height });
            yPos += height + 20;
        });

        // Position right nodes
        yPos = 10;
        targetOnly.forEach(id => {
            const incomingLinks = links.filter(link => link.target === id);
            const totalValue = incomingLinks.reduce((sum, link) => sum + link.value, 0);
            const height = Math.max(20, (totalValue / maxValue) * 100);

            nodePositions.set(id, { x: 550, y: yPos, height });
            yPos += height + 20;
        });

        return (
            <div className="relative h-full w-full overflow-hidden bg-white p-4">
                <svg width="100%" height="100%" viewBox="0 0 600 400">
                    {/* Draw links */}
                    {links.map((link, linkIndex) => {
                        const sourcePos = nodePositions.get(link.source);
                        const targetPos = nodePositions.get(link.target);

                        if (!sourcePos || !targetPos) return null;

                        // Calculate link width based on value
                        const linkWidth = Math.max(1, (link.value / maxValue) * 20);

                        // Calculate source and target Y positions
                        const sourceY = sourcePos.y + sourcePos.height / 2;
                        const targetY = targetPos.y + targetPos.height / 2;

                        // Create bezier curve path
                        const path = `
                            M ${sourcePos.x + 100} ${sourceY}
                            C ${sourcePos.x + 200} ${sourceY},
                              ${targetPos.x - 200} ${targetY},
                              ${targetPos.x} ${targetY}
                        `;

                        return (
                            <g key={`link-${linkIndex}`}>
                                <path
                                    d={path}
                                    stroke={link.color || '#999'}
                                    strokeWidth={linkWidth}
                                    fill="none"
                                    strokeOpacity={0.4}
                                />
                                <title>
                                    {link.source} → {link.target}: {link.value}
                                </title>
                            </g>
                        );
                    })}

                    {/* Draw nodes */}
                    {nodes.map((node, nodeIndex) => {
                        const pos = nodePositions.get(node.id);
                        if (!pos) return null;

                        return (
                            <g key={`node-${nodeIndex}`}>
                                <rect
                                    x={pos.x}
                                    y={pos.y}
                                    width={100}
                                    height={pos.height}
                                    fill={node.color || '#999'}
                                    stroke="#fff"
                                    strokeWidth={1}
                                    rx={4}
                                    ry={4}
                                />
                                <text
                                    x={pos.x + 50}
                                    y={pos.y + pos.height / 2}
                                    textAnchor="middle"
                                    dominantBaseline="middle"
                                    fill="#fff"
                                    fontSize={12}
                                    fontWeight="bold"
                                >
                                    {node.name || node.id}
                                </text>
                                <title>{node.name || node.id}</title>
                            </g>
                        );
                    })}
                </svg>

                {/* Accessibility information */}
                <div className="sr-only">
                    <h2>Sankey Diagram</h2>
                    <ul>
                        {links.map((link, index) => (
                            <li key={index}>
                                {link.source} to {link.target}: {link.value}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        );
    }, [links, nodes]);

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
                <div className="text-xs text-gray-500 mt-1">
                    {nodes.length} nodes, {links.length} connections
                </div>
            </div>

            <div className="h-full w-full">
                <ResponsiveContainer width="95%" height="90%">
                    {renderSankey}
                </ResponsiveContainer>
            </div>
        </div>
    );
}
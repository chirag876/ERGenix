import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib
matplotlib.use('Agg')
import numpy as np

class ERDiagramGenerator:
    def __init__(self):
        self.fig = None
        self.ax = None
        self.table_dimensions = {}  # Stores width/height for each table
        
        # Enhanced color scheme
        self.colors = {
            'header_bg': '#2E86AB',      # Professional blue
            'header_text': '#FFFFFF',     # White text
            'table_bg': '#F8F9FA',       # Light gray background
            'table_border': '#343A40',    # Dark gray border
            'pk_bg': '#FFE5B4',          # Light orange for primary keys
            'fk_bg': '#E3F2FD',          # Light blue for foreign keys
            'relationship': '#E74C3C',    # Red for relationships
            'text': '#2C3E50'            # Dark blue-gray for text
        }
        
    def generate_diagram(self, tables_data, relationships):
        """Generate enhanced ER diagram using matplotlib"""
        plt.style.use('default')
        
        # Create figure with better proportions
        fig, ax = plt.subplots(figsize=(18, 14))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')
        
        # Set background color
        fig.patch.set_facecolor('#FFFFFF')
        
        # Calculate positions for tables with better spacing
        num_tables = len(tables_data)
        positions = self._calculate_positions(num_tables)
        
        # Draw tables with enhanced styling
        table_positions = {}
        for i, (table_name, table_info) in enumerate(tables_data.items()):
            pos = positions[i]
            table_positions[table_name] = pos
            self._draw_table(ax, table_name, table_info['schema'], pos)
        
        # Draw relationships with improved styling
        for rel in relationships:
            self._draw_relationship(ax, rel, table_positions)
        
        # Enhanced title with better styling
        plt.suptitle('ERGenix - Database ER Diagram', 
                    fontsize=24, fontweight='bold', 
                    color=self.colors['header_bg'], 
                    y=0.95, fontfamily='serif')
        
        # Add subtle grid for better visual structure
        self._add_subtle_background(ax)
        
        plt.tight_layout()
        return fig
    
    def _add_subtle_background(self, ax):
        """Add a subtle background pattern"""
        # Add very light grid lines
        for i in range(0, 101, 20):
            ax.axhline(y=i, color='#F0F0F0', linewidth=0.3, alpha=0.5)
            ax.axvline(x=i, color='#F0F0F0', linewidth=0.3, alpha=0.5)
    
    def _calculate_positions(self, num_tables):
        """Calculate optimal positions for tables with better spacing"""
        positions = []
        if num_tables <= 4:
            # Optimized positions for better visual balance
            grid_positions = [(15, 75), (75, 75), (15, 25), (75, 25)]
            positions = grid_positions[:num_tables]
        else:
            # Dynamic grid with improved spacing
            cols = int(np.ceil(np.sqrt(num_tables)))
            rows = int(np.ceil(num_tables / cols))
            
            # Calculate spacing to avoid overlap
            x_spacing = 80 / cols
            y_spacing = 70 / rows
            
            for i in range(num_tables):
                row = i // cols
                col = i % cols
                x = 10 + (col * x_spacing)
                y = 85 - (row * y_spacing)
                positions.append((x, y))
        
        return positions
    
    def _draw_table(self, ax, table_name, schema, position):
        """Draw an enhanced table box with improved styling"""
        x, y = position
        
        # Calculate table dimensions with better proportions
        max_text_width = max(len(table_name), 
                            max(len(f"{col['column']} : {col['type']}") for col in schema))
        width = min(max_text_width * 0.6 + 4, 28)
        row_height = 2.2
        header_height = 3.5
        height = len(schema) * row_height + header_height
        
        # Add shadow effect
        shadow_offset = 0.3
        shadow_rect = patches.Rectangle((x + shadow_offset, y - shadow_offset), 
                                      width, header_height,
                                      linewidth=0, facecolor='#00000020')
        ax.add_patch(shadow_rect)
        
        # Draw table header with gradient-like effect
        header_rect = patches.Rectangle((x, y), width, header_height,
                                      linewidth=2.5, 
                                      edgecolor=self.colors['table_border'],
                                      facecolor=self.colors['header_bg'])
        ax.add_patch(header_rect)
        
        # Add header text with better styling
        ax.text(x + width/2, y + header_height/2, table_name, 
                ha='center', va='center',
                fontweight='bold', fontsize=12,
                color=self.colors['header_text'],
                fontfamily='sans-serif')
        
        # Draw columns with alternating colors and better formatting
        for i, col in enumerate(schema):
            col_y = y - (i + 1) * row_height
            
            # Determine background color based on key type
            if col['key'] == 'PRI':
                bg_color = self.colors['pk_bg']
            elif 'FK' in col.get('key', ''):
                bg_color = self.colors['fk_bg']
            else:
                bg_color = self.colors['table_bg'] if i % 2 == 0 else '#FFFFFF'
            
            # Add shadow for each row
            shadow_rect = patches.Rectangle((x + shadow_offset, col_y - shadow_offset), 
                                          width, row_height,
                                          linewidth=0, facecolor='#00000010')
            ax.add_patch(shadow_rect)
            
            # Draw column rectangle
            col_rect = patches.Rectangle((x, col_y), width, row_height,
                                       linewidth=1.5, 
                                       edgecolor=self.colors['table_border'],
                                       facecolor=bg_color)
            ax.add_patch(col_rect)
            
            # Format column text with better typography
            col_text = f"{col['column']} : {col['type']}"
            prefix = ""
            if col['key'] == 'PRI':
                prefix = "🔑 "  # Key emoji for primary key
            elif 'FK' in col.get('key', ''):
                prefix = "🔗 "  # Link emoji for foreign key
            
            # Add the text with improved positioning
            ax.text(x + 1.5, col_y + row_height/2, prefix + col_text,
                   ha='left', va='center', fontsize=9,
                   color=self.colors['text'],
                   fontweight='medium' if col['key'] == 'PRI' else 'normal',
                   fontfamily='monospace')
        
        # Store table dimensions for relationship drawing
        self.table_dimensions[table_name] = {
            'x': x, 'y': y, 'width': width, 'height': height
        }
    
    def _draw_relationship(self, ax, relationship, table_positions):
        """Draw enhanced relationship lines between tables"""
        from_table = relationship['from_table']
        to_table = relationship['to_table']
        
        if from_table in table_positions and to_table in table_positions:
            from_pos = table_positions[from_table]
            to_pos = table_positions[to_table]
            
            # Calculate better connection points (edges of tables rather than centers)
            from_x, from_y = self._get_connection_point(from_table, to_pos)
            to_x, to_y = self._get_connection_point(to_table, from_pos)
            
            # Draw curved line for better aesthetics
            if abs(from_x - to_x) > abs(from_y - to_y):
                # Horizontal curve
                mid_x = (from_x + to_x) / 2
                curve_x = [from_x, mid_x, mid_x, to_x]
                curve_y = [from_y, from_y, to_y, to_y]
            else:
                # Vertical curve
                mid_y = (from_y + to_y) / 2
                curve_x = [from_x, from_x, to_x, to_x]
                curve_y = [from_y, mid_y, mid_y, to_y]
            
            # Draw the curved relationship line
            ax.plot(curve_x, curve_y, color=self.colors['relationship'],
                   linewidth=2.5, alpha=0.8, linestyle='-')
            
            # Add enhanced arrowhead
            ax.annotate('', xy=(to_x, to_y), xytext=(curve_x[-2], curve_y[-2]),
                       arrowprops=dict(arrowstyle='->', 
                                     color=self.colors['relationship'],
                                     lw=2.5, alpha=0.9))
            
            # Add relationship label if available
            if 'relationship_type' in relationship:
                mid_x = (from_x + to_x) / 2
                mid_y = (from_y + to_y) / 2
                ax.text(mid_x, mid_y, relationship['relationship_type'],
                       ha='center', va='center', fontsize=8,
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', 
                               edgecolor=self.colors['relationship'],
                               alpha=0.9))
    
    def _get_connection_point(self, table_name, target_pos):
        """Calculate the best connection point on the edge of a table"""
        if table_name not in self.table_dimensions:
            # Fallback to center if dimensions not available
            return target_pos
        
        dims = self.table_dimensions[table_name]
        table_center_x = dims['x'] + dims['width'] / 2
        table_center_y = dims['y'] - dims['height'] / 2
        
        target_x, target_y = target_pos
        
        # Determine which edge of the table to connect to
        dx = target_x - table_center_x
        dy = target_y - table_center_y
        
        if abs(dx) > abs(dy):
            # Connect to left or right edge
            if dx > 0:
                # Connect to right edge
                return dims['x'] + dims['width'], table_center_y
            else:
                # Connect to left edge
                return dims['x'], table_center_y
        else:
            # Connect to top or bottom edge
            if dy > 0:
                # Connect to top edge
                return table_center_x, dims['y']
            else:
                # Connect to bottom edge
                return table_center_x, dims['y'] - dims['height']
#version 450

uniform sampler2D tex0;
uniform sampler2D tex1;
uniform sampler2D tex2;
uniform sampler2D tex3;

in vec2 texCoord;
out vec4 fragColor[4];

void main() {
	fragColor[0] = textureLod(tex0, texCoord, 0.0);
	fragColor[1] = textureLod(tex1, texCoord, 0.0);
	fragColor[2] = textureLod(tex2, texCoord, 0.0);
	fragColor[3] = textureLod(tex3, texCoord, 0.0);
}

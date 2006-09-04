<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <xsl:template match="/settings/keys">
 </xsl:template>

 <xsl:template xml:space="preserve" match="/settings/muck">
  <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
  <keys>
    <key name="check" comment="Check" control_key="c"/>
    <key name="call" comment="Call" control_key="c" khotkeys_output="Ctrl+c" khotkeys_input="Win+c"/>
    <key name="raise" comment="Raise" control_key="r" khotkeys_output="Ctrl+r" khotkeys_input="Win+r"/>
    <key name="raise_increase" comment="Raise increase" control_key="Right" khotkeys_output="Ctrl+Right" khotkeys_input="Win+u"/>
    <key name="raise_decrease" comment="Raise decrease" control_key="Left" khotkeys_output="Ctrl+Left" khotkeys_input="Win+d"/>
    <key name="raise_increase_bb" comment="Raise increase BB" control_key="Up" khotkeys_output="Ctrl+Up" khotkeys_input="Win+b"/>
    <key name="raise_decrease_bb" comment="Raise decrease BB" control_key="Down" khotkeys_output="Ctrl+Down" khotkeys_input="Win+v"/>
    <key name="raise_pot" comment="Raise pot" control_key="p" khotkeys_output="Ctrl+p" khotkeys_input="Win+p"/>
    <key name="raise_half_pot" comment="Raise half pot" control_key="h" khotkeys_output="Ctrl+h" khotkeys_input="Win+h"/>
    <key name="fold" comment="Fold" control_key="f" khotkeys_output="Ctrl+f" khotkeys_input="Win+f"/>
  </keys>

 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
